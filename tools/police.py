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
from run_controls import RunControls, RunStopped

SIREN = ["A5:3", "E5:3"]     # two-tone nino-nino
LAPS = 3                     # how many squares to patrol
DRIVE_MS = 2500              # side length (~2x the first run)
TURN_MS = 560                # ~90 deg pivot at PIVOT speed: TUNE THIS
SPEED = 60                   # forward speed
PIVOT = 60                   # pivot speed
FLASH_MS = 120               # light alternation period


def police_flash(car, ms, controls):
    """Alternate headlights while checking B and the run limit."""
    end = running_time() + ms
    left = True
    while running_time() < end:
        controls.check()
        if left:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 255, 0, 0)  # left red
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 0)     # right off
        else:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 0, 0, 0)     # left off
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 255)   # right blue
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
            display.show("P")
            music.play(SIREN, wait=False, loop=True)
            for lap in range(LAPS):
                for side in range(4):
                    controls.check()
                    car.pwmCruiseControl(SPEED, SPEED)
                    police_flash(car, DRIVE_MS, controls)
                    controls.check()
                    display.show(Image.ARROW_NE)
                    car.pwmCruiseControl(PIVOT, -PIVOT)
                    police_flash(car, TURN_MS, controls)
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