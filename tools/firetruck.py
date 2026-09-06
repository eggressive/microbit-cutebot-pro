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

# Siren: "Тръгнал кос" (Тръгнал кос, lyrics Асен Разцветников), EXACT
# transcription from the MuseScore score 7737110 (patrisiyanedy
# arrangement, C major, 4/4) via its MusicXML (trgnal-kos-...mxl).
# Durations straight from the file: eighth = :2, quarter = :4
# (microbit music: 4 ticks per quarter note). Verse = measures 1-8;
# 9-32 are empty filler rests. Structure per measure:
#   m1 G4 E4 E4(quarter) | F4 D4 D4(quarter)      "Тръгнал кос с дълъг нос"
#   m2 C D E F G G G(q)  eighth run               "през гората гол и бос"
#   m3 = m1, m4 C E G G C(q) R(q)                 "тупа с крак ... юнак"
#   m5 D D D D D E F(q)   "Ходил, ходил, па се спрял"
#   m6 E E E E E F G(q)   "три коли мухи изял"
#   m7 = m1, m8 = m4                              closing
SIREN = [
    # m1 "Тръгнал кос с дълъг нос"
    "G4:2", "E4:2", "E4:4",
    "F4:2", "D4:2", "D4:4",
    # m2 "през гората гол и бос"
    "C4:2", "D4:2", "E4:2", "F4:2", "G4:2", "G4:2", "G4:4",
    # m3 "тупа с крак трак-так-так"
    "G4:2", "E4:2", "E4:4",
    "F4:2", "D4:2", "D4:4",
    # m4 "като същ юнак"
    "C4:2", "E4:2", "G4:2", "G4:2", "C4:4", "R:4",
    # m5 "Ходил, ходил, па се спрял"
    "D4:2", "D4:2", "D4:2", "D4:2", "D4:2", "E4:2", "F4:4",
    # m6 "три коли мухи изял"
    "E4:2", "E4:2", "E4:2", "E4:2", "E4:2", "F4:2", "G4:4",
    # m7 "тупнал с крак, тръгнал пак"
    "G4:2", "E4:2", "E4:4",
    "F4:2", "D4:2", "D4:4",
    # m8 "бре-бре, че юнак!"
    "C4:2", "E4:2", "G4:2", "G4:2", "C4:4", "R:4",
]
SIREN_TEMPO = 120  # march tempo for a children's song
LAPS = 3                     # how many squares to patrol
DRIVE_MS = 2500              # side length (~2x the first run)
TURN_MS = 560                # ~90 deg pivot at PIVOT speed: TUNE THIS
SPEED = 60                   # forward speed
PIVOT = 60                   # pivot speed
FLASH_MS = 120               # light alternation period
AVOID_CM = 35                # obstacle distance that triggers a turn
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
