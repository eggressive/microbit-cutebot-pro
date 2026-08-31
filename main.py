from cutebot_pro import *
from AILens import *

car = CutebotPro()
ai = AILENS()
ai.switch_function(Ball)

while True:
    ai.get_image()
    x = ai.get_ball_data()[0]
    if ai.get_ball_color() != "No Ball":
        if x < 90:
            car.pwmCruiseControl(30, 60)
        elif x > 165:
            car.pwmCruiseControl(60, 30)
        else:
            car.pwmCruiseControl(50, 50)
    else:
        car.stopImmediately(CutebotProMotors.ALL)
