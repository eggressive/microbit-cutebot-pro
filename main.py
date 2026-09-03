# Ball chaser v2 (2026-09-03). Fixes over v1, both observed on hardware:
#
# 1) STEERING INVERSION: with v1 (x<90 -> pwm(30,60), x>165 -> pwm(60,30))
#    the car turned AWAY from the ball. Physical wheel mapping is mirrored
#    from what v1 assumed, so v2 swaps the arguments. If v2 turns away too,
#    swap them back AND check the camera is not mounted upside down (its
#    screen text must read normally).
# 2) FRAME STUTTER FIX: the camera pads its stream with zero frames between
#    real detections. v1 saw ball/no-ball alternating and braked every other
#    frame (the "sluggish" feel). v2 stops only after MISS_LIMIT consecutive
#    empty frames.
#
# Telemetry: every 10th detection prints ball x/size to serial (USB REPL).

from cutebot_pro import *
from AILens import *

CENTER_LO = 80    # ball x below this = left of center (wiki case-19 value)
CENTER_HI = 144   # above this = right of center
NEAR_SIZE = 100   # ball this large in view = close enough, stop (wiki case-19)
MISS_LIMIT = 5    # consecutive empty frames before we treat the ball as lost

car = CutebotPro()
ai = AILENS()
ai.switch_function(Ball)

misses = 0
tick = 0

while True:
    ai.get_image()
    color = ai.get_ball_color()
    if color == "Blue" or color == "Red":
        misses = 0
        d = ai.get_ball_data()
        x = d[0]
        size = d[2]
        tick += 1
        if tick % 10 == 0:
            print("ball x", x, "size", size)
        if size >= NEAR_SIZE:
            car.stopImmediately(CutebotProMotors.ALL)
        elif x < CENTER_LO:
            car.pwmCruiseControl(60, 30)   # INVERTED from v1: toward a left ball
        elif x > CENTER_HI:
            car.pwmCruiseControl(30, 60)   # INVERTED from v1: toward a right ball
        else:
            car.pwmCruiseControl(60, 60)  # centered: charge
    else:
        misses += 1
        if misses >= MISS_LIMIT:
            car.stopImmediately(CutebotProMotors.ALL)