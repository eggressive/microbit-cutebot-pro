# Standalone AI Lens test (2026-09-03). Camera ONLY: zero car interaction.
# Proves the camera chain (I2C + init + Ball mode + detection) independent of
# all Cutebot motor-board behavior. Runs with or without the car board.
#
# Display shows: happy face = camera answered init poll; then a live
# direction readout: left arrow / right arrow / center dot while a ball
# is in view, empty grid when nothing is seen.
# Serial (USB) streams every detection for logging.
#
# Flash with: tools/mbpack tools/ --main camtest.py
# (camtest talks raw I2C, no driver import, so a tools/-only pack works)

from microbit import *
import music

CAM = 0x14

display.show(Image.TARGET)          # "searching for camera"
i2c.init()

# init poll (MakeCode initModule port): wait for nonzero byte with timeout
start = running_time()
ready = False
while running_time() - start < 30000:
    try:
        if i2c.read(CAM, 1)[0] != 0:
            ready = True
            break
    except OSError:
        pass
    sleep(100)

if not ready:
    display.scroll("NO CAM")
    while True:
        display.set_pixel(2, 2, 9)
        sleep(300)
        display.set_pixel(2, 2, 0)
        sleep(300)

display.show(Image.HAPPY)
music.pitch(1000, 100)
sleep(1000)

# Ball mode
i2c.write(CAM, bytearray([0x20, 7]))
sleep(500)

ARROW_L = Image('00900:00990:09999:00990:00900:')
ARROW_R = Image('00900:09900:99999:09900:00900:')
CENTER = Image('00000:00900:09990:00900:00000:')

misses = 0
while True:
    d = list(i2c.read(CAM, 9))
    if d[0] == 7 and (d[1] == 1 or d[1] == 2):
        misses = 0
        x = d[2]
        size = d[4]
        color = "BLUE" if d[1] == 1 else "RED"
        print(color, "x", x, "y", d[3], "size", size)
        if x < 80:
            display.show(ARROW_L)       # ball image-left
        elif x > 144:
            display.show(ARROW_R)       # ball image-right
        else:
            display.show(CENTER)
    else:
        misses += 1
        if misses >= 10:
            display.clear()
    sleep(100)