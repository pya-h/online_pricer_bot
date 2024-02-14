import threading
from time import time
from typing import Callable

class Planner:
    def __init__(self, interval: float, callback: Callable[..., None]):
        self.interval = interval
        self.callback = callback
        self.Planner = None
        self.is_running = False
        self.started_at: int = time() // 60


    def start(self):
        if not self.is_running:
            self.Planner = threading.Timer(60 * self.interval, self._run_callback)
            self.Planner.start()
            self.is_running = True
            print("Planner started.")

    def stop(self):
        if self.is_running:
            self.Planner.cancel()
            self.is_running = False
            print("Planner stopped.")

    def _run_callback(self):
        self.callback()
        self.is_running = False

    def minutes_running(self) -> int:
        return (time() // 60) - self.started_at
