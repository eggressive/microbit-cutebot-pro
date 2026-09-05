"""Physical A starts a fresh run; B or a time limit ends it."""
from microbit import button_a, button_b, running_time, sleep

MAX_RUN_MS = 60000
POLL_MS = 20


class RunStopped(Exception):
    pass


class RunControls:
    def wait_for_start(self):
        # Discard presses during boot, a previous run or cleanup. A held button
        # must be released before a new press can start the robot.
        button_a.was_pressed()
        button_b.was_pressed()
        released = False
        while True:
            a = button_a.was_pressed()
            b = button_b.was_pressed()
            a_down = button_a.is_pressed()
            b_down = button_b.is_pressed()
            if b or b_down:
                released = False
            elif released and a:
                self.started = running_time()
                return
            elif not a_down:
                released = True
            sleep(POLL_MS)

    def check(self):
        button_a.was_pressed()  # A while running is not a queued restart.
        b = button_b.was_pressed()
        elapsed = running_time() - self.started
        if b or button_b.is_pressed() or elapsed < 0 or elapsed >= MAX_RUN_MS:
            raise RunStopped()

    def wait(self, ms):
        # Replace long sleeps without changing the requested segment duration.
        start = running_time()
        while True:
            self.check()
            left = ms - (running_time() - start)
            if left <= 0:
                return
            sleep(min(POLL_MS, left))
