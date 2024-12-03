from time import time
from typing import Callable
from apscheduler.schedulers.background import BackgroundScheduler


class Planner:
    def __init__(self, interval: float, callback: Callable[..., any], *params):
        self.interval: float = interval
        self.callback: Callable[..., None] = callback
        self.last_call_result: any = None
        self.params: list | tuple = params
        self.is_running: bool = False
        self.started_at: int = None
        self.scheduler: BackgroundScheduler = BackgroundScheduler()
        self.scheduler.add_job(self._run_callback, "interval", seconds=interval * 60)

    def start(self):
        if not self.is_running:
            self.scheduler.start()
            self.started_at: int = time() // 60
            self.is_running = True
            print("Planner started.")

    def stop(self):
        if self.is_running:
            # self.scheduler.cancel()
            self.scheduler.shutdown()
            self.is_running = False
            print("Planner stopped.")

    def _run_callback(self):
        self.last_call_result = self.callback()
        # self.is_running = False

    def minutes_running(self) -> int:
        return (time() // 60) - self.started_at
