"""Host-only linefollow regressions; no physical timing claims.

Run: python3 -m unittest discover -s tests -v
Locks the P-controller sign convention against observed wheel wiring:
offset < 0 (line left of car, car drifting right) -> speed up LEFT wheel
to steer back left. Matches the mirrored-steering fix in main.py and the
cardhunt pivot swap.
"""
import unittest

from test_motor_cleanup import HardwareStub, EndSimulation, STOP


def make_frames(n):
    # cmd 0x60 [0x01] read returns 2 bytes: big-endian offset+3000
    return None  # placeholder; tests drive offsets directly


def drives(stub):
    return [(t, e[2]) for t, e in stub.timed_events
            if e[0] == "write" and e[1] == 0x10 and e[2][2] == 0x10 and e[2] != STOP]


class LinefollowSteeringTests(unittest.TestCase):
    """Offset -> wheel speed mapping must match the mirrored chassis wiring.
    Ball-chaser (observed on hardware): target on left drives (60, 30) ->
    pivots LEFT. So on this chassis, faster LEFT wheel means LEFT turn.
    Positive offset = car is RIGHT of the line -> must steer LEFT -> left
    wheel must be the SLOWER one (right wheel speeds up)."""

    def simulate_with_offset(self, offset, **kw):
        # Offset wire format: car.getOffset() returns ((b[0]<<8)|b[1]) - 3000
        wire = offset + 3000
        frame = bytes([wire >> 8, wire & 0xFF])
        stub = HardwareStub(frames=iter([frame] * 200), auto_finish=True, **kw)
        # linefollow issues a 0x60 command then reads 2 bytes from the car.
        orig_read = stub.read

        def read2(address, length):
            if length == 2 and address == 0x10:
                return frame
            return orig_read(address, length)

        stub.read = read2
        error = stub.run("tools/linefollow.py")
        self.assertIsInstance(error, (EndSimulation, KeyboardInterrupt))
        return stub

    def test_offset_zero_drives_straight(self):
        stub = self.simulate_with_offset(0, a_presses=[(100, 140)], end_ms=600)
        self.assertTrue(drives(stub))
        move = drives(stub)[0][1]
        # full frame: FF F9 10 04 wheel_sel left right direction
        self.assertEqual(move[5], move[6])

    def test_positive_offset_steers_left(self):
        stub = self.simulate_with_offset(1500, a_presses=[(100, 140)], end_ms=600)
        move = drives(stub)[0][1]
        left_speed = move[5]
        right_speed = move[6]
        self.assertLess(left_speed, right_speed,
                        "positive offset (car right of line) must slow LEFT "
                        "wheel so the faster right wheel pivots the car left")

    def test_negative_offset_steers_right(self):
        stub = self.simulate_with_offset(-1500, a_presses=[(100, 140)], end_ms=600)
        move = drives(stub)[0][1]
        left_speed = move[5]
        right_speed = move[6]
        self.assertGreater(left_speed, right_speed,
                           "negative offset (car left of line) must speed LEFT "
                           "wheel so the faster left wheel pivots the car right")

    def test_b_stops_mid_run(self):
        stub = self.simulate_with_offset(0,
                                         a_presses=[(100, 140)],
                                         b_presses=[(250, 300)],
                                         end_ms=900)
        self.assertTrue(drives(stub))
        stops = [t for t, e in stub.timed_events
                 if t >= 250 and e == ("write", 0x10, STOP)]
        self.assertTrue(stops)


if __name__ == "__main__":
    unittest.main()
