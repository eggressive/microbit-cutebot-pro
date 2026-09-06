"""Host-only button and readiness regressions; no physical timing claims."""
import itertools
import unittest

from test_motor_cleanup import BALL, DEMOS, STOP, HardwareStub, EndSimulation

SCRIPTS = ("main.py",) + DEMOS


def movements(stub):
    return [(t, e[2]) for t, e in stub.timed_events
            if e[0] == "write" and e[1] == 0x10 and e[2][2] == 0x10 and e[2] != STOP]


def stopped_after(stub, when):
    return [t for t, e in stub.timed_events if t >= when and e == ("write", 0x10, STOP)]


class RunControlsTests(unittest.TestCase):
    def simulate(self, script, **kwargs):
        stub = HardwareStub(frames=itertools.repeat(BALL), auto_finish=False, **kwargs)
        error = stub.run(script)
        self.assertIsInstance(error, EndSimulation)
        return stub

    def test_boot_waits_without_driving_or_siren(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[], end_ms=300)
                self.assertEqual(movements(stub), [])
                self.assertNotIn(("music_play",), stub.events)

    def test_a_starts_each_demo(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 140)], end_ms=300)
                self.assertTrue(movements(stub))
                self.assertGreaterEqual(movements(stub)[0][0], 100)

    def test_b_stops_and_latches_until_fresh_a(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 140)],
                                     b_presses=[(250, 300)], end_ms=700)
                stops = stopped_after(stub, 250)
                self.assertTrue(stops)
                self.assertLessEqual(stops[0] - 250, 35)
                self.assertTrue(movements(stub))
                self.assertTrue(all(t < stops[0] for t, _ in movements(stub)))
                self.assertNotIn(("display", "YES"), stub.events)
                if script in DEMOS:
                    self.assertIn(("music_stop",), stub.events)

    def test_restart_is_a_new_run_not_resume(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 140), (500, 540)],
                                     b_presses=[(250, 300)], end_ms=700)
                moves = movements(stub)
                first = next(frame for t, frame in moves if t < 250)
                restarted = next(frame for t, frame in moves if t >= 500)
                self.assertEqual(first, restarted)
                self.assertFalse(any(285 <= t < 500 for t, _ in moves))

    def test_b_wins_over_simultaneous_a(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 140)],
                                     b_presses=[(100, 140)], end_ms=400)
                self.assertEqual(movements(stub), [])

    def test_a_held_at_boot_must_be_released_then_pressed(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(0, 250), (400, 440)], end_ms=600)
                self.assertTrue(movements(stub))
                self.assertGreaterEqual(movements(stub)[0][0], 400)

    def test_a_held_through_b_does_not_restart(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 600)],
                                     b_presses=[(250, 300)], end_ms=800)
                stop = stopped_after(stub, 250)[0]
                self.assertFalse(any(t > stop for t, _ in movements(stub)))

    def test_short_b_press_between_polls_is_not_lost(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 140)],
                                     b_presses=[(251, 252)], end_ms=600)
                self.assertLessEqual(stopped_after(stub, 251)[0] - 251, 35)

    def test_b_during_camera_read_prevents_new_motor_command(self):
        stub = self.simulate("main.py", a_presses=[(100, 140)],
                             b_presses=[(115, 116)], end_ms=350)
        self.assertGreater(stub.camera_reads, 0)
        self.assertEqual(movements(stub), [])

    def test_ball_run_expires_after_sixty_seconds(self):
        stub = self.simulate("main.py", a_presses=[(100, 140)], end_ms=61000)
        self.assertTrue(movements(stub))
        stops = stopped_after(stub, 60100)
        self.assertTrue(stops)
        self.assertLessEqual(stops[0], 60140)
        self.assertFalse(any(t > stops[0] for t, _ in movements(stub)))

    def test_completed_demos_wait_for_a_and_do_not_auto_repeat(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 50000)], end_ms=55000)
                self.assertEqual(stub.events.count(("display", "YES")), 1)
                moves = movements(stub)
                self.assertEqual(len(moves), 24 if script.endswith(("police.py", "firetruck.py")) else 2)

    def test_all_demos_enforce_limit_and_allow_explicit_restart(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 140), (500, 540)],
                                     run_limit_ms=200, end_ms=900)
                first_stop = stopped_after(stub, 301)[0]
                self.assertLessEqual(first_stop, 335)
                self.assertFalse(any(first_stop < t < 500 for t, _ in movements(stub)))
                self.assertTrue(any(t >= 500 for t, _ in movements(stub)))
                self.assertNotIn(("display", "YES"), stub.events)

    def test_a_pressed_while_running_is_not_queued_after_b(self):
        for script in SCRIPTS:
            with self.subTest(script=script):
                stub = self.simulate(script, a_presses=[(100, 140), (220, 230)],
                                     b_presses=[(250, 300)], end_ms=700)
                stop = stopped_after(stub, 250)[0]
                self.assertFalse(any(t > stop for t, _ in movements(stub)))

    def test_completed_demo_accepts_new_a(self):
        stub = self.simulate("tools/figure8.py", a_presses=[(100, 140), (12000, 12040)], end_ms=24000)
        self.assertEqual(stub.events.count(("display", "YES")), 2)
        self.assertEqual(len(movements(stub)), 4)

    def test_camera_timeout_refuses_mode_switch_and_motion(self):
        for response in (bytes([0]), OSError("camera missing")):
            with self.subTest(response=repr(response)):
                stub = HardwareStub(camera_init_reply=response, a_presses=[(100, 40000)],
                                    frames=itertools.repeat(BALL), end_ms=40000)
                error = stub.run("main.py")
                self.assertIsInstance(error, OSError)
                self.assertNotIsInstance(error, EndSimulation)
                self.assertIn("ready", str(error).lower())
                self.assertEqual(movements(stub), [])
                self.assertFalse(any(e[0] == "write" and e[1] == 0x14 for e in stub.events))
                self.assertIn(("display", "NO"), stub.events)

    def test_press_during_camera_initialization_is_not_queued(self):
        stub = self.simulate("main.py", camera_ready_at=500,
                             a_presses=[(100, 140), (700, 740)], end_ms=900)
        self.assertTrue(movements(stub))
        self.assertGreaterEqual(movements(stub)[0][0], 700)

    def test_b_stop_failure_remains_fatal_and_cleans_up_siren(self):
        for script in DEMOS:
            with self.subTest(script=script):
                stub = HardwareStub(a_presses=[(100, 140), (500, 540)],
                                    b_presses=[(250, 300)], stop_fails=True, end_ms=800)
                self.assertIsInstance(stub.run(script), OSError)
                self.assertIn(("music_stop",), stub.events)
                self.assertFalse(any(t >= 500 for t, _ in movements(stub)))


if __name__ == "__main__":
    unittest.main()
