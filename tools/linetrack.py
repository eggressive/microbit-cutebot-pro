# AI Lens line follower (2026-09-05). Uses the camera's Tracking mode
# (mode 8) to detect the line and steer toward it. Different from
# tools/linefollow.py, which uses the 4-way IR grayscale sensor.
#
# Camera data layout in Tracking mode (per pxt-PlanetX-AI main.ts):
#   DataBuff[0] = 8 (mode echo)
#   DataBuff[1] = angle
#   DataBuff[2] = trend byte: <90 line veers LEFT, >130 line veers RIGHT,
#                 else straight
#   DataBuff[3..] = width, length, etc.
#
# Controls: A start, B stop and latch, 60s cap. Camera must be ready.
#
# Display: "A" idle, "-" while tracking, "L"/"R" when the trend byte says
# the line is off-center, "." when no line in view (car holds last command).
#
# Mounting: lens should look down at the line ahead, roughly 30-45 degrees
# off vertical. A lens pointed at the horizon sees nothing.
#
# Flash with: tools/flash-demo tools/linetrack.py

from microbit import display
from cutebot_pro import CutebotPro, CutebotProMotors
from AILens import AILENS, Tracking
from run_controls import RunControls, RunStopped, POLL_MS

BASE_SPEED = 22
TURN_SPEED = 30
TREND_LEFT = 90    # trend byte below this = line leans left
TREND_RIGHT = 130  # above this = line leans right

car = CutebotPro()
car.stopImmediately(CutebotProMotors.ALL)
ai = AILENS()
if not ai.ready:
    from microbit import Image
    display.show(Image.NO)
    raise OSError("AI Lens not ready; restart after checking camera")
ai.switch_function(Tracking)
controls = RunControls()

while True:
    display.show("A")
    controls.wait_for_start()
    display.show("-")
    last_cmd = None
    try:
        while True:
            controls.check()
            ai.get_image()
            controls.check()
            trend = ai.get_track_data()[1]

            if trend == 0:
                # No line in view; hold last known command.
                if last_cmd is None:
                    car.stopImmediately(CutebotProMotors.ALL)
                else:
                    car.pwmCruiseControl(*last_cmd)
                controls.wait(POLL_MS)
                continue

            if trend < TREND_LEFT:
                car.pwmCruiseControl(TURN_SPEED, BASE_SPEED)
                last_cmd = (TURN_SPEED, BASE_SPEED)
                display.show("L")
            elif trend > TREND_RIGHT:
                car.pwmCruiseControl(BASE_SPEED, TURN_SPEED)
                last_cmd = (BASE_SPEED, TURN_SPEED)
                display.show("R")
            else:
                car.pwmCruiseControl(BASE_SPEED, BASE_SPEED)
                last_cmd = (BASE_SPEED, BASE_SPEED)
                display.show("-")
            controls.wait(POLL_MS)
    except RunStopped:
        pass  # Deliberate stop only. Hardware errors still terminate.
    finally:
        car.stopImmediately(CutebotProMotors.ALL)
