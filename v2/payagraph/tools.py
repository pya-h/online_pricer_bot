from typing import Callable
from time import time


class ParallelJob:
    '''Define objects from this and use it in TelegramBot, it will does some parallel jobs in the bot by a specific interval [in minutes]'''
    def __init__(self, interval: int, function: Callable[..., any], *params) -> None:
        self.interval: int = interval
        self.function: Callable[..., any] = function
        self.last_run_result: any = None
        self.last_call_minutes: int = None
        self.params: list[any] = params
        self.running: bool = False


    def go(self):
        '''Start running...'''
        self.last_call_minutes = time() // 60
        self.running = True
        return self

    def do(self):
        self.last_run_result = self.function(*self.params)
        self.last_call_minutes = time() // 60

    def stop(self):
        self.running = False
