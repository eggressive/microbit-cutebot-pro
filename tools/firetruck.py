# Fire truck demo (2026-09-05). Clone of the police car: same square
# patrol and obstacle avoidance, but with a fire-truck wail siren and
# red beacon lights. Camera not needed.
# Flash with: tools/flash-demo tools/firetruck.py
#
# Tuning knobs (measured values, adjust to your floor/battery):
#   DRIVE_MS  - how long each side of the square is
#   TURN_MS   - pivot time that lands closest to 90 degrees; tune this first
#   AVOID_CM  - obstacle distance that triggers a turn
#   REVERSE_MS - how long to back up before pivoting away
#   AVOID_TURN_MS - pivot time when avoiding an obstacle
# Display: F = fire patrol, arrow = turning, YES = done. Siren loops.
#
# Sonar note: ultrasonic() returns 0 on no valid echo (blocking, ~100ms).
# Treat 0 as "clear" and only react to 0 < d < AVOID_CM, so a failed read
# never triggers a phantom turn. Two consecutive hits are required before
# reacting, so a single spurious echo does not cause a phantom turn.

from cutebot_pro import *
from microbit import *
import music
from run_controls import RunControls, RunStopped

# US fire-truck wail: two-tone alternation between a low and high pitch.
# E5 (~659 Hz) and A#5/Bb5 (~932 Hz) approximate the classic mechanical
# Q-siren wail. Fast tempo and short notes blur the pair into a siren sound.
SIREN = ["E5:4", "A#5:4"]
SIREN_TEMPO = 240  # beats per minute; fast enough to blur into a wail
LAPS = 3                     # how many squares to patrol
DRIVE_MS = 2500              # side length (~2x the first run)
TURN_MS = 560                # ~90 deg pivot at PIVOT speed: TUNE THIS
SPEED = 60                   # forward speed
PIVOT = 60                   # pivot speed
FLASH_MS = 120               # light alternation period
AVOID_CM = 25                # obstacle distance that triggers a turn
REVERSE_MS = 400             # back up before pivoting away
AVOID_TURN_MS = 560          # pivot time when avoiding an obstacle


def fire_flash(car, ms, controls):
    """Flash both headlights red together (beacon) while checking B/limit."""
    end = running_time() + ms
    on = True
    while running_time() < end:
        controls.check()
        if on:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 255, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 255, 0, 0)
        else:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 0, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 0)
        on = not on
        controls.wait(FLASH_MS)


def drive_side(car, ms, controls):
    """Drive forward one side, flashing and polling sonar. Return True if an
    obstacle was detected (caller backs up and pivots away). Sonar is polled
    every 3rd flash cycle: ultrasonic() is ~60ms (3 reads), and polling every
    cycle would starve the B/run-limit checks. Two consecutive obstacle
    readings are required before turning, so a single spurious echo does not
    cause a phantom turn on a clear floor."""
    end = running_time() + ms
    on = True
    tick = 0
    hits = 0
    while running_time() < end:
        controls.check()
        if on:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 255, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 255, 0, 0)
        else:
            car.singleHeadlights(CutebotProRGBLight.RGBL, 0, 0, 0)
            car.singleHeadlights(CutebotProRGBLight.RGBR, 0, 0, 0)
        on = not on
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
            display.show("F")
            music.set_tempo(ticks=4, bpm=SIREN_TEMPO)
            music.play(SIREN, wait=False, loop=True)
            turn_left = True  # alternate avoidance direction
            for lap in range(LAPS):
                for side in range(4):
                    controls.check()
                    car.pwmCruiseControl(SPEED, SPEED)
                    if drive_side(car, DRIVE_MS, controls):
                        # obstacle: back up, pivot away, then resume the square
                        car.stopImmediately(CutebotProMotors.ALL)
                        display.show(Image.ARROW_NE)
                        car.pwmCruiseControl(-SPEED, -SPEED)
                        fire_flash(car, REVERSE_MS, controls)
                        car.stopImmediately(CutebotProMotors.ALL)
                        if turn_left:
                            car.pwmCruiseControl(PIVOT, -PIVOT)
                        else:
                            car.pwmCruiseControl(-PIVOT, PIVOT)
                        turn_left = not turn_left
                        fire_flash(car, AVOID_TURN_MS, controls)
                        car.pwmCruiseControl(SPEED, SPEED)
                        display.show("F")
                    controls.check()
                    display.show(Image.ARROW_NE)
                    car.pwmCruiseControl(PIVOT, -PIVOT)
                    fire_flash(car, TURN_MS, controls)
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
