# Cutebot Pro driver, V2 hardware only (V2.0.2 / V2.1.0). ~4.5KB, fits the micro:bit V2
# filesystem together with AILens.py and main.py (total budget ~20.6KB measured).
#
# Trimmed from ELECFREAKS EF_Produce_MicroPython cutebot_pro.py:
#   - V1 code branches removed (V1 units talk the old 0x99 frame protocol)
#   - debug prints removed
#   - servo control added (was missing from the official Python driver)
#
# Protocol reference: elecfreaks/pxt-Cutebot-Pro v2.ts (the MakeCode extension
# ELECFREAKS ships, treated as ground truth where it disagrees with the Python driver).
from microbit import i2c, pin8, pin12, sleep
import time
import machine

I2C_ADDR = 0x10


class CutebotProMotors:
    M1 = 1  # left wheel
    M2 = 2  # right wheel
    ALL = 3


class CutebotProRGBLight:
    RGBR = 1
    RGBL = 2
    RGBA = 3


class CutebotProSpeedUnits:
    Cms = 0
    Ins = 1


class SonarUnit:
    Centimeters = 0
    Inches = 1


class CutebotProServo:
    S1 = 1
    S2 = 2
    S3 = 3
    S4 = 4


class CutebotPro:
    def __init__(self):
        if I2C_ADDR not in i2c.scan():
            raise OSError("Cutebot Pro not on I2C: is the motor board powered (battery)?")

    def _cmd(self, command, params):
        i2c.write(I2C_ADDR, bytes([0xFF, 0xF9, command, len(params)] + params))
        sleep(1)

    def _read(self, n):
        return i2c.read(I2C_ADDR, n)

    # --- motors ---
    def pwmCruiseControl(self, speedL, speedR):
        """Wheel speeds -100..100. Negative = reverse."""
        direction = 0
        if speedL < 0:
            direction |= 0x01
        if speedR < 0:
            direction |= 0x02
        self._cmd(0x10, [2, abs(speedL), abs(speedR), direction])

    def fullSpeedAhead(self):
        self._cmd(0x10, [2, 100, 100, 0])

    def fullAstern(self):
        self._cmd(0x10, [2, 100, 100, 0x03])

    def stopImmediately(self, wheel):
        wheel_map = {1: 0, 2: 1, 3: 2}
        self._cmd(0x10, [wheel_map.get(wheel, 2), 0, 0, 0])

    def readSpeed(self, motor, speedUnits=CutebotProSpeedUnits.Cms):
        self._cmd(0xA0, [motor])  # M1=1, M2=2
        sleep(1)
        speed = self._read(1)[0]
        return speed if speedUnits == CutebotProSpeedUnits.Cms else speed / 0.3937

    def readDistance(self, motor):
        """Wheel rotation in degrees since last clear."""
        self._cmd(0xA0, [motor + 2])  # M1 -> 3, M2 -> 4
        sleep(1)
        data = self._read(4)
        distance = data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24)
        if distance & 0x80000000:
            distance -= 0x100000000
        return distance

    def clearWheelTurn(self, motor):
        # v2.ts sends the raw 0-based index (M1->0, M2->1). The official Python
        # driver sends motor+2 here (3/4), which contradicts v2.ts - likely a
        # copy-paste bug from readDistance. If clearing misbehaves on real
        # hardware, try self._cmd(0x50, [motor + 2]) instead.
        self._cmd(0x50, [motor - 1])

    # --- headlights ---
    def singleHeadlights(self, light, r, g, b):
        light_map = {1: 1, 2: 0, 3: 2}  # enum -> wire: 0=left, 1=right, 2=all
        self._cmd(0x20, [light_map.get(light, 2), abs(r), abs(g), abs(b)])

    def colorLight(self, light, color):
        self.singleHeadlights(light, (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)

    def turnOffAllHeadlights(self):
        self._cmd(0x20, [2, 0, 0, 0])

    # --- 4-way line following ---
    def trackbitStateValue(self):
        self._cmd(0x60, [0x00])
        sleep(1)
        self.fourWayStateValue = self._read(1)[0]
        return self.fourWayStateValue

    def getOffset(self):
        """-3000 (far left) .. +3000 (far right), 0 = centered on line."""
        self._cmd(0x60, [0x01])
        sleep(1)
        data = self._read(2)
        return ((data[0] << 8) | data[1]) - 3000

    # --- ultrasonic (GPIO pins 8/12, not I2C) ---
    def ultrasonic(self, unit=SonarUnit.Centimeters, maxCmDistance=500):
        readings = []
        for _ in range(3):
            d = self._sonar_single(maxCmDistance)
            if 0 < d < maxCmDistance:
                readings.append(d)
            sleep(20)
        if not readings:
            return 0
        readings.sort()
        result = readings[len(readings) // 2]
        return result if unit == SonarUnit.Centimeters else int(result * 0.3937)

    def _sonar_single(self, maxCmDistance):
        pin8.write_digital(0)
        time.sleep_us(5)
        pin8.write_digital(1)
        time.sleep_us(10)
        pin8.write_digital(0)
        echo_us = machine.time_pulse_us(pin12, 1, maxCmDistance * 58)
        if echo_us < 0:
            return 0
        return int(echo_us / 58)

    # --- servo (added; protocol from v2.ts extendServoControl, ServoType=180deg) ---
    def setServo(self, index, angle):
        """Standard 180-degree servo on port S1-S4. index: 1-4, angle: 0-180."""
        if index < 1 or index > 4:
            raise ValueError("Servo index must be 1..4")
        if angle < 0:
            angle = 0
        elif angle > 180:
            angle = 180
        self._cmd(0x40, [index - 1, angle])

    # --- version ---
    def readVersions(self):
        self._cmd(0xA0, [0x00])
        sleep(1)
        v = self._read(3)
        return "V {}.{}.{}".format(v[0], v[1], v[2])