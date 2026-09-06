"""Host-only regression checks for display state, driver bounds and unit math.

Run: python3 -m unittest discover -s tests -v
Covers main.py display letters (running vs idle), AILens.py card/color ID
bounds, and cutebot_pro.py cm/s to in/s conversion. No physical timing claims.
"""
import unittest
from pathlib import Path

from test_motor_cleanup import HardwareStub, BALL

ROOT = Path(__file__).resolve().parents[1]


def _load_ailens():
    stub = HardwareStub(frames=iter([BALL]))
    spec = __import__("importlib.util").util.spec_from_file_location(
        "AILens_host", ROOT / "AILens.py")
    module = __import__("importlib.util").util.module_from_spec(spec)
    import sys
    sys.modules["microbit"] = __import__("microbit")
    spec.loader.exec_module(module)
    return module


def _lens_with_frame(frame):
    module = _load_ailens()
    lens = object.__new__(module.AILENS)
    lens._AILENS__Data_buff = list(frame)
    return lens


class DisplayTests(unittest.TestCase):
    def test_main_running_indicator_is_arrow_not_b_letter(self):
        src = __import__("pathlib").Path(ROOT / "main.py").read_text()
        self.assertIn('display.show("A")', src)
        self.assertNotIn('display.show("B")', src)
        self.assertIn('display.show("G")', src)


class AILensBoundsTests(unittest.TestCase):
    def test_number_card_id_zero_returns_no_card(self):
        lens = _lens_with_frame([2, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_card_content(), "No Card")

    def test_number_card_id_within_range(self):
        lens = _lens_with_frame([2, 5, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_card_content(), "4")

    def test_number_card_above_range_returns_no_card(self):
        lens = _lens_with_frame([2, 11, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_card_content(), "No Card")

    def test_letter_card_id_zero_returns_no_card(self):
        lens = _lens_with_frame([4, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_card_content(), "No Card")

    def test_other_card_id_zero_no_longer_returns_last_entry(self):
        lens = _lens_with_frame([3, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_card_content(), "No Card")

    def test_other_card_at_upper_bound(self):
        lens = _lens_with_frame([3, 20, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_card_content(), "Back")

    def test_other_card_above_range_returns_no_card(self):
        lens = _lens_with_frame([3, 21, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_card_content(), "No Card")

    def test_color_id_zero_no_longer_returns_white(self):
        lens = _lens_with_frame([9, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_color_type(), "No Color")

    def test_color_id_within_range(self):
        lens = _lens_with_frame([9, 5, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_color_type(), "Red")

    def test_color_id_above_range_returns_no_color(self):
        lens = _lens_with_frame([9, 7, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(lens.get_color_type(), "No Color")


class SpeedConversionTests(unittest.TestCase):
    def _make_car(self, speed_byte):
        stub = HardwareStub(frames=iter([BALL]))
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location(
            "cutebot_pro_host", ROOT / "cutebot_pro.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["microbit"] = __import__("microbit")
        spec.loader.exec_module(module)
        car = object.__new__(module.CutebotPro)
        captured = {}
        car._cmd = lambda cmd, params: captured.setdefault("cmd", cmd)
        car._read = lambda n: bytes([speed_byte])
        return module, car

    def test_cms_unchanged(self):
        module, car = self._make_car(100)
        speed = car.readSpeed(1, module.CutebotProSpeedUnits.Cms)
        self.assertEqual(speed, 100)

    def test_inches_applies_cm_to_inch_factor(self):
        module, car = self._make_car(100)
        speed = car.readSpeed(1, module.CutebotProSpeedUnits.Ins)
        self.assertAlmostEqual(speed, 100 / 2.54, places=3)


if __name__ == "__main__":
    unittest.main()
