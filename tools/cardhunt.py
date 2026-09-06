# Road-sign treasure hunt (2026-09-05). The kid shows a motion card to the
# AI Lens, the car executes it as a bounded step, then waits for the NEXT
# card. Same card twice in a row acts once, so a held card cannot loop a turn.
#
# Cards (ELECFREAKS command cards, part of "otherCards" group):
#   Stop       -> brakes and latches stopped until A
#   Forward    -> 1s at CARD_SPEED
#   Back       -> 1s reverse
#   Turn left  -> 500ms pivot in place (left wheel back, right wheel forward)
#   Turn right -> 500ms pivot the other way
#
# Note: observed hardware wiring maps "(-, +)" to a left pivot and "(+, -)"
# to a right pivot; matches main.py's mirrored steering fix.
#
# Display: "A" idle / waiting for A press, "C" waiting for a card, the shown
# card's initial letter while executing a step, "G" when done with a step
# (and ready for the next card). Same-card-repeat: ignored until a different
# card or no card has been seen since.
#
# Buttons: A starts a fresh run and clears stop latch, B wins anytime.
# Camera gate: refuses to arm if the lens is not ready at boot.
# Flash with: tools/mbpack tools/ --main cardhunt.py

from microbit import display, Image, sleep
from cutebot_pro import CutebotPro, CutebotProMotors
from AILens import AILENS, Card
from run_controls import RunControls, RunStopped

CARD_SPEED = 40
STEP_MS = 1000
TURN_MS = 500
STOP_CARD = "Stop"

ACTIONS = {
    "Forward": (CARD_SPEED, CARD_SPEED, STEP_MS),
    "Back": (-CARD_SPEED, -CARD_SPEED, STEP_MS),
    "Turn left": (-CARD_SPEED, CARD_SPEED, TURN_MS),
    "Turn right": (CARD_SPEED, -CARD_SPEED, TURN_MS),
}
DISPLAY_BY_CARD = {
    "Stop": "S",
    "Forward": "F",
    "Back": "B",
    "Turn left": "L",
    "Turn right": "R",
}

car = CutebotPro()
car.stopImmediately(CutebotProMotors.ALL)
ai = AILENS()
if not ai.ready:
    display.show(Image.NO)
    raise OSError("AI Lens not ready; restart after checking camera")
ai.switch_function(Card)
controls = RunControls()
while True:
    display.show("A")
    controls.wait_for_start()
    display.show("C")
    last_card = None
    try:
        while True:
            controls.check()
            ai.get_image()
            controls.check()  # B during the read wins over this frame.
            card = ai.get_card_content()

            if card == "No Card":
                last_card = None
                continue

            if card == last_card:
                # Held card already acted once; wait for it to clear.
                continue

            last_card = card

            if card == STOP_CARD or card not in ACTIONS:
                car.stopImmediately(CutebotProMotors.ALL)
                if card == STOP_CARD:
                    display.show("S")
                    # Hold stopped until a fresh card appears.
                    continue
                display.show("?")
                sleep(400)
                display.show("C")
                continue

            left, right, ms = ACTIONS[card]
            display.show(DISPLAY_BY_CARD[card])
            car.pwmCruiseControl(left, right)
            controls.wait(ms)  # B can interrupt mid-step
            car.stopImmediately(CutebotProMotors.ALL)
            display.show("C")
    except RunStopped:
        pass  # Deliberate stop only. Hardware errors still terminate.
    finally:
        car.stopImmediately(CutebotProMotors.ALL)