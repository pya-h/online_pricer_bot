from typing import Callable

from telegram.error import Conflict


class ApiKeyManager:

    def __init__(self, initial_api_key: str, change_event: Callable[[str], None], change_trigger: int = 3):
        self.keys = [initial_api_key] if initial_api_key else []
        self.current = 0
        self.failures_count = 0
        self.change_trigger = change_trigger
        self.change_event = change_event

    def use_next(self):
        if (count := len(self.keys)) <= 1:
            return
        self.current = (self.current + 1) % count
        self.change_event(self.keys[self.current])
        self.failures_count = 0

    def add(self, *new_keys: str):
        for api_key in new_keys:
            if api_key in self.keys:
                raise Conflict(f"API key already exists: {api_key}")
            self.keys.append(api_key)

    def discard(self, *api_keys: str):
        for api_key in api_keys:
            if api_key not in self.keys:
                raise Conflict(f"No such API key: {api_key}")
            self.keys.remove(api_key)

    def fail(self):
        self.failures_count += 1
        if self.failures_count >= self.change_trigger:
            self.use_next()

    def ok(self):
        self.failures_count = 0

    @property
    def api_key(self) -> str:
        return self.keys[self.current]

    @property
    def report(self) -> str:
        return f'''API Keys: {len(self.keys)}
Current: {self.api_key}
Current Index: {self.current + 1}
Recent Rapid Failures: {self.failures_count}
'''