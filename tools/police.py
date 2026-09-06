# Police car demo with obstacle avoidance (2026-09-05).
# Drives a square patrol, flashes red/blue headlights, plays a two-tone
# siren, and pivots away when the ultrasonic sensor sees an obstacle
# during a side. Camera not needed. Flash with: tools/flash-demo tools/police.py
#
# Tuning knobs (measured values, adjust to your floor/battery):
#   DRIVE_MS  - how long each side of the square is
#   TURN_MS   - pivot time that lands closest to 90 degrees; tune this first
#   AVOID_CM  - obstacle distance that triggers a turn
#   AVOID_TURN_MS - pivot time when avoiding an obstacle
# Display: P = patrol, arrow = turning, YES = done. Siren loops in background.
#
# Sonar note: ultrasonic() returns 0 on no valid echo (blocking, ~100ms).
# Treat 0 as "clear" and only react to 0 < d < AVOID_CM, so a failed read
# never triggers a phantom turn.

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
AVOID_CM = 20                # obstacle distance that triggers a turn
AVOID_TURN_MS = 560          # pivot time when avoiding an obstacle


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


def drive_side(car, ms, controls):
    """Drive forward one side, flashing and polling sonar. Return True if an
    obstacle was detected (caller pivots away). Sonar is polled every 3rd
    flash cycle: ultrasonic() is ~60ms (3 reads), and polling every cycle
    would starve the B/run-limit checks. Two consecutive obstacle readings
    are required before turning, so a single spurious echo does not cause
    a phantom turn on a clear floor."""
    end = running_time() + ms
    left = True
    tick = 0
    hits = 0
    while running_time() < end:
        controls.check()
        if left:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 255, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 0)
        else:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 0, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 255)
        left = not left
        tick += 1
        if tick % 3 == 0:
            d = car.ultrasonic()
            if 0 < d < AVOID_CM:
                hits += 1
                if hits >= 2:
                    return True
            else:
                hits = 0
        controls.wait(FLASH_MS)
    return False


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
                    if drive_side(car, DRIVE_MS, controls):
                        # obstacle: stop, pivot away, then resume the square
                        car.stopImmediately(CutebotProMotors.ALL)
                        display.show(Image.ARROW_NE)
                        car.pwmCruiseControl(PIVOT, -PIVOT)
                        police_flash(car, AVOID_TURN_MS, controls)
                        car.pwmCruiseControl(SPEED, SPEED)
                        display.show("P")
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
