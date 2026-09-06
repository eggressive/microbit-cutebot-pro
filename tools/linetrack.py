# AI Lens line follower (2026-09-05). Uses the camera's Tracking mode
# (mode 8) to detect the line and steer toward it. Different from
# tools/linefollow.py, which uses the 4-way IR grayscale sensor.
#
# Camera data layout in Tracking mode (per pxt-PlanetX-AI main.ts and
# observed on hardware 2026-09-05):
#   DataBuff[0] = 8 (mode echo)
#   DataBuff[1] = angle (continuous): ~24 = line far LEFT, ~163 = far RIGHT,
#                 ~90-100 = centered. This is the steering signal.
#   DataBuff[2] = trend byte: <90 left, >130 right, else straight (coarse)
#   DataBuff[3] = length
#
# Steering: proportional on the angle byte. error = angle - CENTER;
# positive error (line right) slows the left wheel so the faster right
# wheel turns the car right (matches the observed mirrored chassis).
#
# Controls: A start, B stop and latch, 60s cap. Camera must be ready.
#
# Display: "A" idle, "-" while tracking, "." when no line in view.
#
# Mounting: lens looks down at the line ahead, ~30-45 deg off vertical.
# Aim it so the line reads angle ~90-100 when centered (see the serial
# probe in the project note). A lens aimed too shallow sees the line at
# the frame edge and the car drives straight.
#
# Flash with: tools/flash-demo tools/linetrack.py

from microbit import display
from cutebot_pro import CutebotPro, CutebotProMotors
from AILens import AILENS, Tracking
from run_controls import RunControls, RunStopped, POLL_MS

BASE_SPEED = 22
MAX_CORRECTION = 20   # wheel delta at full angle error
CENTER = 95           # angle byte value when the line is centered
KP_NUM = 20           # correction = (angle - CENTER) * KP_NUM / KP_DEN
KP_DEN = 60           # at angle 24 or 163, error ~70 -> correction ~23 (clamped)

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
            track = ai.get_track_data()
            angle = track[0]   # DataBuff[1], the continuous steering signal

            if angle == 0:
                # No line in view; hold last known command.
                if last_cmd is None:
                    car.stopImmediately(CutebotProMotors.ALL)
                else:
                    car.pwmCruiseControl(*last_cmd)
                display.show(".")
                controls.wait(POLL_MS)
                continue

            error = angle - CENTER
            corr = (error * KP_NUM) // KP_DEN
            if corr > MAX_CORRECTION:
                corr = MAX_CORRECTION
            elif corr < -MAX_CORRECTION:
                corr = -MAX_CORRECTION
            left = BASE_SPEED - corr
            right = BASE_SPEED + corr
            car.pwmCruiseControl(left, right)
            last_cmd = (left, right)
            display.show("-")
            controls.wait(POLL_MS)
    except RunStopped:
        pass  # Deliberate stop only. Hardware errors still terminate.
    finally:
        car.stopImmediately(CutebotProMotors.ALL)
