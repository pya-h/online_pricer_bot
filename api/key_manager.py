from typing import Callable
from telegram.error import Conflict
from api.base import BaseAPIService
from tools import manuwriter
from tools.exceptions import CacheFailureException
import json


class ApiKeyManager:

    def __init__(
        self,
        initial_api_key: str,
        change_event: Callable[[str], None],
        change_trigger: int = 3,
        keystore_filename="keys",
    ):
        self.current = 0
        self.failures_count = 0
        self.change_trigger = change_trigger
        self.change_event = change_event
        self.keystore_filename = keystore_filename if ".json" in keystore_filename else f"{keystore_filename}.json"
        if self.keystore_filename and self.load():
            self.change_event(self.keys[self.current])
            if initial_api_key not in self.keys:
                self.keys.append(initial_api_key)
        else:
            self.keys = [initial_api_key] if initial_api_key else []

    def use_next(self):
        if (count := len(self.keys)) <= 1:
            return
        self.current = (self.current + 1) % count
        self.change_event(self.keys[self.current])
        self.failures_count = 0
        self.save()

    def add(self, *new_keys: str):
        for api_key in new_keys:
            if api_key in self.keys:
                raise Conflict(f"API key already exists: {api_key}")
            self.keys.append(api_key)
            self.save()

    def discard(self, *api_keys: str):
        for api_key in api_keys:
            if api_key not in self.keys:
                raise Conflict(f"No such API key: {api_key}")
            self.keys.remove(api_key)
            self.save()

    def fail(self):
        self.failures_count += 1
        if self.failures_count >= self.change_trigger:
            self.use_next()

    def ok(self):
        self.failures_count = 0

    def load(self) -> list | dict:
        """Read cache and convert it to python dict/list."""
        try:
            keystore = open(f"./{BaseAPIService.cacheFolderPath}/{self.keystore_filename}", "r")
            str_json = keystore.read()
            keystore.close()
            saved_keys = json.loads(str_json)
            if saved_keys and ("keys" in saved_keys) and saved_keys["keys"]:
                self.keys = saved_keys["keys"]
                self.current = saved_keys["current"]
                return len(self.keys) > 0
        except:
            pass
        return False

    def save(self) -> None:
        if not manuwriter.prepare_folder(BaseAPIService.cacheFolderPath):
            manuwriter.log(
                "Saving Api Keys failed! It seems that api/cache folder does not exists!",
                category_name="KeyMan.fux",
            )
            return
        manuwriter.fwrite_from_scratch(
            f"./{BaseAPIService.cacheFolderPath}/{self.keystore_filename}",
            json.dumps({"keys": self.keys, "current": self.current}),
            "KeyMan.fux",
        )

    @property
    def api_key(self) -> str:
        return self.keys[self.current]

    @property
    def report(self) -> str:
        return f"API Keys: {len(self.keys)}\nCurrent: {self.api_key}\nCurrent Index: {self.current + 1}\nRecent Rapid Failures: {self.failures_count}"

    @property
    def state(self) -> str:
        return "\n".join([(key if index != self.current else f"{key} ✅") for index, key in enumerate(self.keys)])
