"""Host-only control-flow checks, not micro:bit hardware emulation.

Run: python3 -m unittest discover -s tests -v
This directory is not included by mbpack's non-recursive source selection.
"""
import importlib.util
from pathlib import Path
import runpy
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
STOP = bytes.fromhex("ff f9 10 04 02 00 00 00")
LIGHTS_OFF = bytes.fromhex("ff f9 20 04 02 00 00 00")
BALL = bytes([7, 1, 112, 100, 30, 30, 90, 1, 1])
DEMOS = ("tools/police.py", "tools/figure8.py")


class HardwareStub:
    """Record actual driver writes and inject faults at hardware boundaries."""

    def __init__(self, frames=(), fail=None, exception=None,
                 stop_fails=False, lights_off_fails=False, music_stop_fails=False):
        self.frames = iter(frames)
        self.fail = fail
        self.exception = exception if exception is not None else OSError("injected fault")
        self.stop_fails = stop_fails
        self.lights_off_fails = lights_off_fails
        self.music_stop_fails = music_stop_fails
        self.events = []
        self.clock = 0
        self.driving = False
        self.faulted = False
        self.camera_reads = 0

    def trip(self, point):
        if self.fail == point:
            self.faulted = True
            raise self.exception

    def scan(self):
        self.events.append(("scan",))
        self.trip("scan")
        return [0x10, 0x14]

    def read(self, address, length):
        if length == 1 and address == 0x14:
            self.events.append(("camera_init",))
            return bytes([7])
        if length == 9 and address == 0x14:
            self.camera_reads += 1
            self.events.append(("camera_read", self.camera_reads))
            try:
                frame = next(self.frames)
            except StopIteration:
                self.faulted = True
                raise KeyboardInterrupt("end of test frames")
            if isinstance(frame, BaseException):
                self.faulted = True
                raise frame
            return frame
        raise AssertionError("Unexpected I2C read")

    def write(self, address, data):
        data = bytes(data)
        self.events.append(("write", address, data))
        if address == 0x14:
            self.trip("camera_mode")
        elif data[2] == 0x10:
            if data == STOP:
                self.trip("startup_stop")
                if self.stop_fails and (self.driving or self.faulted):
                    raise OSError("injected stop failure")
                self.driving = False
            else:
                self.driving = True
                self.trip("drive")
        elif data == LIGHTS_OFF:
            if self.lights_off_fails:
                raise OSError("injected lights-off failure")
        elif data[2] == 0x20:
            self.trip("headlights")

    def sleep(self, ms):
        self.clock += ms
        if self.driving and ms > 1:
            self.trip("sleep")

    def show(self, image):
        self.events.append(("display", image))

    def music_play(self, *args, **kwargs):
        self.events.append(("music_play",))
        self.trip("music_play")

    def music_stop(self):
        self.events.append(("music_stop",))
        if self.music_stop_fails:
            raise RuntimeError("injected music-stop failure")

    def run(self, script):
        microbit = types.ModuleType("microbit")
        pin = types.SimpleNamespace(write_digital=lambda v: None)
        microbit.__dict__.update(
            i2c=types.SimpleNamespace(
                init=lambda: None, scan=self.scan, read=self.read, write=self.write),
            sleep=self.sleep, running_time=lambda: self.clock, pin8=pin, pin12=pin,
            Image=types.SimpleNamespace(ARROW_NE="NE", YES="YES"),
            display=types.SimpleNamespace(show=self.show, scroll=self.show))
        music = types.ModuleType("music")
        music.__dict__.update(play=self.music_play, stop=self.music_stop)
        machine = types.ModuleType("machine")
        # Restore sys.modules after every execution so no test leaks its stub.
        with patch.dict(sys.modules, microbit=microbit, music=music, machine=machine):
            for name in ("cutebot_pro", "AILens"):
                spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
                assert spec is not None and spec.loader is not None
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
            try:
                runpy.run_path(str(ROOT / script), run_name="__main__")
            except BaseException as exc:
                return exc
        return None

    def motor_commands(self):
        return [e[2] for e in self.events
                if e[0] == "write" and e[1] == 0x10 and e[2][2] == 0x10]


class MotorCleanupTests(unittest.TestCase):
    def assert_started_stopped(self, stub):
        self.assertTrue(stub.motor_commands())
        self.assertEqual(stub.motor_commands()[0], STOP)

    def assert_demo_cleanup(self, stub):
        events = stub.events
        self.assertIn(("write", 0x10, STOP), events)
        self.assertIn(("music_stop",), events)
        self.assertIn(("write", 0x10, LIGHTS_OFF), events)
        last_stop = max(i for i, e in enumerate(events) if e == ("write", 0x10, STOP))
        music_stop = events.index(("music_stop",))
        lights_off = events.index(("write", 0x10, LIGHTS_OFF))
        self.assertLess(last_stop, music_stop)
        self.assertLess(music_stop, lights_off)
        self.assertNotIn(("display", "YES"), events)

    def test_ball_stops_before_camera_init(self):
        stub = HardwareStub()
        self.assertIsInstance(stub.run("main.py"), KeyboardInterrupt)
        self.assert_started_stopped(stub)
        self.assertLess(stub.events.index(("write", 0x10, STOP)),
                        stub.events.index(("camera_init",)))

    def test_ball_camera_error_and_interrupt_after_motion_stop(self):
        for fault in (OSError("camera disconnected"), KeyboardInterrupt("Ctrl-C")):
            with self.subTest(fault=type(fault).__name__):
                stub = HardwareStub(frames=[BALL, fault])
                self.assertIs(stub.run("main.py"), fault)
                self.assert_started_stopped(stub)
                self.assertEqual(stub.motor_commands(),
                                 [STOP, bytes.fromhex("ff f9 10 04 02 3c 3c 00"), STOP])

    def test_ball_mode_failure_also_stops(self):
        stub = HardwareStub(fail="camera_mode")
        self.assertIs(stub.run("main.py"), stub.exception)
        self.assertEqual(stub.motor_commands(), [STOP, STOP])

    def test_ball_driver_failure_also_stops(self):
        stub = HardwareStub(frames=[BALL], fail="drive")
        self.assertIs(stub.run("main.py"), stub.exception)
        self.assertEqual(stub.motor_commands()[-1], STOP)

    def test_ball_failed_stop_is_not_silenced(self):
        stub = HardwareStub(frames=[BALL, OSError("camera disconnected")], stop_fails=True)
        error = stub.run("main.py")
        self.assertIsInstance(error, OSError)
        self.assertEqual(str(error), "injected stop failure")
        self.assertEqual(stub.motor_commands()[-1], STOP)

    def test_ball_steering_near_and_reacquisition_unchanged(self):
        left = bytes([7, 1, 40, 100, 30, 30, 90, 1, 1])
        right = bytes([7, 2, 180, 100, 30, 30, 90, 1, 1])
        near = bytes([7, 1, 112, 100, 110, 110, 90, 1, 1])
        stub = HardwareStub(frames=[left, right, BALL, near] + [bytes(9)] * 5 + [BALL])
        self.assertIsInstance(stub.run("main.py"), KeyboardInterrupt)
        forward = bytes.fromhex("ff f9 10 04 02 3c 3c 00")
        self.assertEqual(stub.motor_commands(), [
            STOP, bytes.fromhex("ff f9 10 04 02 3c 1e 00"),
            bytes.fromhex("ff f9 10 04 02 1e 3c 00"), forward,
            STOP, STOP, forward, STOP])

    def test_demo_normal_motion_and_cleanup(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub()
                self.assertIsNone(stub.run(script))
                self.assert_started_stopped(stub)
                self.assertEqual(stub.motor_commands()[-1], STOP)
                self.assertLess(stub.events.index(("write", 0x10, STOP)),
                                stub.events.index(("music_play",)))
                self.assertEqual(stub.events[-4:], [
                    ("write", 0x10, STOP), ("music_stop",),
                    ("write", 0x10, LIGHTS_OFF), ("display", "YES")])
                speeds = [(c[5], c[6], c[7]) for c in stub.motor_commands()[1:-1]]
                expected = ([(60, 60, 0), (60, 60, 2)] * 12
                            if script.endswith("police.py") else [(30, 65, 0), (65, 30, 0)])
                self.assertEqual(speeds, expected)

    def test_demo_faults_and_interrupts_cleanup(self):
        for script in DEMOS:
            for point in ("drive", "headlights", "sleep", "music_play"):
                for fault in (OSError("peripheral failure"), KeyboardInterrupt("Ctrl-C")):
                    with self.subTest(script=script, point=point, fault=type(fault).__name__):
                        stub = HardwareStub(fail=point, exception=fault)
                        self.assertIs(stub.run(script), fault)
                        self.assert_started_stopped(stub)
                        self.assert_demo_cleanup(stub)

    def test_demo_cleanup_continues_when_stop_fails(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(fail="headlights", stop_fails=True)
                self.assertIsInstance(stub.run(script), OSError)
                self.assert_demo_cleanup(stub)

    def test_demo_normal_completion_stop_failure_does_not_show_success(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(stop_fails=True)
                self.assertIsInstance(stub.run(script), OSError)
                self.assert_demo_cleanup(stub)

    def test_demo_lights_cleanup_continues_when_music_stop_fails(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(music_stop_fails=True)
                self.assertIsInstance(stub.run(script), RuntimeError)
                self.assert_demo_cleanup(stub)

    def test_demo_failed_lights_off_is_not_silenced(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(lights_off_fails=True)
                self.assertIsInstance(stub.run(script), OSError)
                self.assert_demo_cleanup(stub)

    def test_demo_all_cleanup_attempted_when_both_i2c_cleanups_fail(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(fail="headlights", stop_fails=True, lights_off_fails=True)
                self.assertIsInstance(stub.run(script), OSError)
                self.assert_demo_cleanup(stub)

    def test_failed_startup_stop_prevents_motion(self):
        for script in ("main.py",) + DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(frames=[BALL], fail="startup_stop")
                self.assertIsInstance(stub.run(script), OSError)
                self.assertEqual(stub.motor_commands(), [STOP, STOP])
                self.assertNotIn(("music_play",), stub.events)
                if script in DEMOS:
                    self.assert_demo_cleanup(stub)

    def test_missing_car_does_not_start_siren_or_motion(self):
        for script in ("main.py",) + DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(fail="scan")
                self.assertIs(stub.run(script), stub.exception)
                self.assertEqual(stub.motor_commands(), [])
                self.assertNotIn(("music_play",), stub.events)


if __name__ == "__main__":
    unittest.main()
