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

SIREN = ["A5:3", "E5:3"]     # two-tone nino-nino
CIRCLE_MS = 5200             # ms per full loop: THE TUNING KNOB
OUTER = 65                   # outer wheel speed in a turn
INNER = 30                   # inner wheel speed in a turn
FLASH_MS = 120               # light alternation period


def police_flash(car, ms):
    """Alternate left-red / right-blue for `ms` milliseconds (blocking)."""
    end = running_time() + ms
    left = True
    while running_time() < end:
        if left:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 255, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 0)
        else:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 0, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 255)
        left = not left
        sleep(FLASH_MS)


display.show("8")
music.play(SIREN, wait=False, loop=True)

car = CutebotPro()

# loop 1: circle to the LEFT (left wheel inner/slow, right wheel outer/fast)
car.pwmCruiseControl(INNER, OUTER)
police_flash(car, CIRCLE_MS)

# loop 2: circle to the RIGHT (mirror the speeds), crossing the start point
car.pwmCruiseControl(OUTER, INNER)
police_flash(car, CIRCLE_MS)

car.stopImmediately(CutebotProMotors.ALL)
music.stop()
car.turnOffAllHeadlights()
display.show(Image.YES)
