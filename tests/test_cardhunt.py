"""Host-only cardhunt regressions; no physical timing claims.

Run: python3 -m unittest discover -s tests -v
"""
import itertools
import unittest

from test_motor_cleanup import (
    DEMOS, STOP, HardwareStub, EndSimulation,
)

# Frame helpers: 9-byte I2C read layout. otherCards index list (AILens.py):
# [Mouse, micro:bit, Ruler, Cat, Peer, Ship, Apple, Car, Pan, Dog, Umbrella,
#  Airplane, Clock, Grape, Cup, Turn left, Turn right, Forward, Stop, Back]
# ID 16=Turn left, 17=Turn right, 18=Forward, 19=Stop, 20=Back.
def card_frame(card_id):
    return bytes([3, card_id, 128, 100, 30, 30, 90, 1, 1])


def no_card_frame():
    return bytes(9)


FORWARD = card_frame(18)
BACK = card_frame(20)
LEFT = card_frame(16)
STOP_CARD = card_frame(19)
NOT_A_CARD = no_card_frame()


def drives(stub):
    return [(t, e[2]) for t, e in stub.timed_events
            if e[0] == "write" and e[1] == 0x10 and e[2][2] == 0x10 and e[2] != STOP]


def stops(stub):
    return [t for t, e in stub.timed_events if e == ("write", 0x10, STOP)]


class CardhuntTests(unittest.TestCase):
    def simulate(self, frames, **kwargs):
        stub = HardwareStub(frames=iter(frames), auto_finish=True, **kwargs)
        error = stub.run("tools/cardhunt.py")
        self.assertIsInstance(error, (EndSimulation, KeyboardInterrupt))
        return stub

    def test_boot_waits_for_a_and_no_card(self):
        stub = self.simulate([NOT_A_CARD] * 5,
                             a_presses=[(100, 140)], end_ms=400)
        self.assertEqual(drives(stub), [])

    def test_forward_card_drives_once_then_stops(self):
        frames = [NOT_A_CARD, FORWARD, NOT_A_CARD, NOT_A_CARD]
        stub = self.simulate(frames, a_presses=[(100, 140)], end_ms=2500)
        self.assertTrue(drives(stub))
        # forward move then a stop after the step
        self.assertGreaterEqual(len(stops(stub)), 1)

    def test_same_card_twice_acts_once_until_cleared(self):
        frames = [FORWARD, FORWARD, FORWARD, NOT_A_CARD, FORWARD]
        stub = self.simulate(frames, a_presses=[(100, 140)], end_ms=5000)
        # exactly 2 forward movements, not 4
        self.assertEqual(len(drives(stub)), 2)

    def test_unknown_card_shows_question_no_drive(self):
        frames = [card_frame(1), STOP_CARD]  # Mouse card -> not actionable
        stub = self.simulate(frames, a_presses=[(100, 140)], end_ms=2500)
        self.assertEqual(drives(stub), [])
        self.assertIn(("display", "?"), stub.events)

    def test_stop_card_between_moves_brakes(self):
        frames = [FORWARD, NOT_A_CARD, STOP_CARD, STOP_CARD, NOT_A_CARD]
        stub = self.simulate(frames, a_presses=[(100, 140)], end_ms=4000)
        first_move = drives(stub)[0][0]
        later_stops = [t for t in stops(stub) if t > first_move]
        self.assertGreaterEqual(len(later_stops), 1)

    def test_b_interrupts_mid_step(self):
        # Long frames keep the card visible; B lands during the 1s forward step.
        stub = self.simulate([FORWARD] * 10,
                             a_presses=[(100, 140)],
                             b_presses=[(200, 240)],
                             end_ms=2000)
        first_move = drives(stub)[0][0]
        stop_after_b = [t for t in stops(stub) if 200 <= t < first_move + 1100]
        self.assertTrue(stop_after_b)

    def test_no_motion_without_camera(self):
        stub = HardwareStub(
            frames=iter([]),
            camera_ready_at=999999,  # never ready
            a_presses=[(100, 140)],
            auto_finish=True, end_ms=2000,
        )
        # Camera init keeps polling; nothing else runs. No drives, no frames.
        error = stub.run("tools/cardhunt.py")
        self.assertIsInstance(error, (EndSimulation, KeyboardInterrupt))
        self.assertEqual(drives(stub), [])


if __name__ == "__main__":
    unittest.main()
