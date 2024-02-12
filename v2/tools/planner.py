import threading

class Planner:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.Planner = None
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.Planner = threading.Planner(self.interval, self._run_callback)
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
