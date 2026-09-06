# IR line follower (2026-09-05). Uses the 4-way line sensor on the Cutebot
# Pro's front underside. Get an offset (-3000..+3000, 0 = centered on the
# line), scale it to a differential speed correction, apply on top of a
# small base cruise. No camera involved; this one is pure IR.
#
# Controls: same pattern as cardhunt. A to start, B to stop and latch,
# 60s cap via RunControls. No camera gate (camera is unused).
#
# Display: "A" idle, "-" while following, "L" or "R" briefly on strong
# corrections. B stops mid-step.
#
# Tape note: black electrical tape on a light floor works best. Start with
# straight lines and gentle curves; a too-sharp turn exceeds BASE_SPEED
# minus the correction and the car spins instead. KP (proportional gain)
# is the tuning knob; raise it if the car drifts off gentle curves, lower
# it if it oscillates.
#
# Flash with: tools/mbpack tools/ --main linefollow.py, or pack a folder
# that contains only linefollow-as-main.py + cutebot_pro.py + run_controls.py
# (no AILens.py needed).

from microbit import display
from cutebot_pro import CutebotPro, CutebotProMotors
from run_controls import RunControls, RunStopped

BASE_SPEED = 18      # slow forward cruise; the line sensor is close to the ground
MAX_CORRECTION = 22  # wheel delta at full offset
KP_NUM = 22          # gain numerator (correction = offset * KP_NUM / KP_DEN)
KP_DEN = 3000        # gain denominator; at 3000 the correction saturates

car = CutebotPro()
car.stopImmediately(CutebotProMotors.ALL)
controls = RunControls()

while True:
    display.show("A")
    controls.wait_for_start()
    display.show("-")
    try:
        while True:
            controls.check()
            offset = car.getOffset()
            # clamp and scale: offset -3000..+3000 -> correction -22..+22.
            # Observed hardware: faster left wheel pivots left (main.py's
            # mirrored steering and cardhunt's pivot-swap). Positive offset
            # (car RIGHT of line) needs a left steer: left wheel slower.
            # corr = -(offset * KP_NUM / KP_DEN), then left = base -|corr|
            # when offset>0. Implemented as left=base+corr, right=base-corr
            # with corr negated below.
            if offset > 3000:
                offset = 3000
            elif offset < -3000:
                offset = -3000
            corr = -((offset * KP_NUM) // KP_DEN)
            left = BASE_SPEED + corr
            right = BASE_SPEED - corr
            car.pwmCruiseControl(left, right)
            controls.wait(40)  # B wins; tighter loop than the chaser needs
    except RunStopped:
        pass  # Deliberate stop only. Hardware errors still terminate.
    finally:
        car.stopImmediately(CutebotProMotors.ALL)
