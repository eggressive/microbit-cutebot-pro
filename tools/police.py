# Police car demo (2026-09-03): drive a square, flash red/blue headlights,
# play a two-tone siren on the micro:bit V2 built-in speaker.
# Camera not needed. Flash with: tools/flash-demo tools/police.py
#
# Tuning knobs (measured values, adjust to your floor/battery):
#   DRIVE_MS  - how long each side of the square is
#   TURN_MS   - pivot time that lands closest to 90 degrees; tune this first
# Display: P = patrol, arrow = turning, YES = done. Siren loops in background.

from cutebot_pro import *
from microbit import *
import music

SIREN = ["A5:3", "E5:3"]     # two-tone dee-daa
LAPS = 3                     # how many squares to patrol
DRIVE_MS = 2500              # side length (~2x the first run)
TURN_MS = 560                # ~90 deg pivot at PIVOT speed: TUNE THIS
SPEED = 60                   # forward speed
PIVOT = 60                   # pivot speed
FLASH_MS = 120               # light alternation period


def police_flash(car, ms):
    """Alternate left-red / right-blue for `ms` milliseconds (blocking)."""
    end = running_time() + ms
    left = True
    while running_time() < end:
        if left:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 255, 0, 0)  # left red
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 0)     # right off
        else:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 0, 0, 0)     # left off
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 255)   # right blue
        left = not left
        sleep(FLASH_MS)


display.show("P")
music.play(SIREN, wait=False, loop=True)   # siren runs in the background

car = CutebotPro()

for lap in range(LAPS):
    for side in range(4):
        # forward along one side of the square
        car.pwmCruiseControl(SPEED, SPEED)
        police_flash(car, DRIVE_MS)
        # pivot ~90 degrees clockwise: left wheel fwd, right wheel back
        display.show(Image.ARROW_NE)
        car.pwmCruiseControl(PIVOT, -PIVOT)
        police_flash(car, TURN_MS)

car.stopImmediately(CutebotProMotors.ALL)
music.stop()
car.turnOffAllHeadlights()
display.show(Image.YES)