# Stage 1 smoke test: prove car + micro:bit chain with no extra hardware.
# This is the ONLY file flashed for the first test. It avoids all optional modules.
# Success sequence: HAPPY -> "GO" -> headlights blue -> drive pattern
#   -> headlights green, display shows YES.
# Flash it by: tools/mbpack --main smoketest.py tools/  (from repo root)
# (mbpack packs every .py in the target dir; for this test pack ONLY this file,
#  so run it with tools/ as the directory and --main smoketest.py.)

from microbit import *
import music

CAR = 0x10


def cmd(c, params):
    i2c.write(CAR, bytearray([0xFF, 0xF9, c, len(params)] + params))


def headlights(r, g, b):
    # light 2 = both headlights; params: [light, r, g, b]
    cmd(0x20, [2, r, g, b])


def drive(left, right, ms):
    # cmd 0x10 = motorControl(wheel, leftSpeed, rightSpeed, direction), per v2.ts:
    # byte 1 is a WHEEL SELECTOR (0=left, 1=right, 2=all), not a mode.
    # 2 = all wheels. Zero speeds = the canonical V2 stop (there is no
    # dedicated HALT command; stopImmediately in the driver sends [2,0,0,0]).
    direction = (0x01 if left < 0 else 0) | (0x02 if right < 0 else 0)
    cmd(0x10, [2, abs(left), abs(right), direction])
    sleep(ms)


def stop():
    # Byte-identical to the driver's stopImmediately(CutebotProMotors.ALL):
    # both emit FF F9 10 04 02 00 00 00.
    cmd(0x10, [2, 0, 0, 0])


# --- 1. I2C: the car board must answer at 0x10 ---
i2c.init()
car_found = CAR in i2c.scan()
display.show(Image.HAPPY if car_found else Image.SAD)
sleep(1000)
if not car_found:
    # Nothing else can work without the motor board. Halt with a clear signal.
    display.scroll("NO CAR")
    while True:
        display.set_pixel(2, 2, 9)
        sleep(200)
        display.set_pixel(2, 2, 0)
        sleep(200)

display.scroll("GO")

# --- 2. Headlights blue: proves the i2c.write path to the motor board ---
headlights(0, 0, 255)
sleep(500)

# --- 3. Motors: forward, reverse, pivot, forward, stop ---
display.show("F")
music.pitch(1000, 100)
drive(50, 50, 1000)
drive(-50, -50, 800)
drive(50, 0, 600)
drive(50, 50, 1000)
stop()

# --- 4. Green = passed ---
headlights(0, 255, 0)
display.show(Image.YES)
music.pitch(1500, 200)
while True:
    sleep(1000)
