"""Host-only regression checks for display state, driver bounds and unit math.

Run: python3 -m unittest discover -s tests -v
Covers main.py display letters (running vs idle), AILens.py card/color ID
bounds, and cutebot_pro.py cm/s to in/s conversion. No physical timing claims.
"""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def _make_microbit():
    pin = types.SimpleNamespace(write_digital=lambda v: None)
    microbit = types.ModuleType("microbit")
    microbit.__dict__.update(
        i2c=types.SimpleNamespace(init=lambda: None, scan=lambda: [],
                                  read=lambda a, n: bytes(n), write=lambda a, b: None),
        sleep=lambda ms: None, running_time=lambda: 0,
        pin8=pin, pin12=pin,
        Image=types.SimpleNamespace(ARROW_NE="NE", YES="YES", NO="NO", ARROW_E="E"),
        display=types.SimpleNamespace(show=lambda x: None, scroll=lambda x: None))
    return microbit


def _load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, microbit=_make_microbit(), machine=types.ModuleType("machine")):
        spec.loader.exec_module(module)
    return module


def _lens_with_frame(frame):
    module = _load_module("AILens")
    lens = object.__new__(module.AILENS)
    lens._AILENS__Data_buff = list(frame)
    return lens


class DisplayTests(unittest.TestCase):
    def test_main_running_indicator_is_g_not_b(self):
        src = (ROOT / "main.py").read_text()
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
        module = _load_module("cutebot_pro")
        car = object.__new__(module.CutebotPro)
        car._cmd = lambda cmd, params: None
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
