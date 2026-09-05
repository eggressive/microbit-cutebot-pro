# Police figure-of-8 (2026-09-04): two mirrored circles, crossing in the middle.
# Constant differential wheel speeds trace arcs: LEFT circle = (OUTER, INNER),
# RIGHT circle = (INNER, OUTER). Equal CIRCLE_MS = symmetric loops.
# Siren + red/blue strobe run throughout (non-blocking music + flash loop).
# Flash with: tools/flash-demo tools/figure8.py
#
# Tuning: CIRCLE_MS is the one knob: time for one ~360 degree loop.
#   Loops don't close (car ends rotated)? scale CIRCLE_MS proportionally:
#   overshoot 90deg -> *0.75; undershoot 90deg -> *1.33.
# Display: 8 = running, YES = done.

from cutebot_pro import *
from microbit import *
import music
from run_controls import RunControls, RunStopped

SIREN = ["A5:3", "E5:3"]     # two-tone nino-nino
CIRCLE_MS = 5200             # ms per full loop: THE TUNING KNOB
OUTER = 65                   # outer wheel speed in a turn
INNER = 30                   # inner wheel speed in a turn
FLASH_MS = 120               # light alternation period


def police_flash(car, ms, controls):
    """Alternate headlights while checking B and the run limit."""
    end = running_time() + ms
    left = True
    while running_time() < end:
        controls.check()
        if left:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 255, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 0)
        else:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 0, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 255)
        left = not left
        controls.wait(FLASH_MS)


car = CutebotPro()
try:
    # Start stopped; do not start the siren if the motor board is unavailable.
    car.stopImmediately(CutebotProMotors.ALL)
    controls = RunControls()
    display.show("A")
    while True:
        controls.wait_for_start()
        done = False
        try:
            controls.check()
            display.show("8")
            music.play(SIREN, wait=False, loop=True)
            for left, right in ((INNER, OUTER), (OUTER, INNER)):
                controls.check()
                car.pwmCruiseControl(left, right)
                police_flash(car, CIRCLE_MS, controls)
            controls.check()
            done = True
        except RunStopped:
            pass
        finally:
            try:
                car.stopImmediately(CutebotProMotors.ALL)
            finally:
                try:
                    music.stop()
                finally:
                    car.turnOffAllHeadlights()
        display.show(Image.YES if done else "A")
finally:
    # Attempt every cleanup even if one fails; do not hide errors or show success.
    try:
        car.stopImmediately(CutebotProMotors.ALL)
    finally:
        try:
            music.stop()
        finally:
            car.turnOffAllHeadlights()