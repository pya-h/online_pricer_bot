from typing import Callable
from time import time
from models.channel import Channel
from models.account import Account
from bot.post import PostMan


class ParallelJob:
    """Define objects from this and use it in TelegramBot, it will does some parallel jobs in the bot by a specific interval [in minutes]"""

    def __init__(self, interval: int, function: Callable[..., any], *params) -> None:
        self.interval: int = interval
        self.function: Callable[..., any] = function
        self.last_run_result: any = None
        self.last_call_time: int = None
        self.params: list[any] = params
        self.running: bool = False

    def go(self):
        """Start running..."""
        self.last_call_time = time() // 60
        self.running = True
        return self

    def do(self):
        self.last_run_result = self.function(*self.params)
        self.last_call_time = time() // 60

    def stop(self):
        self.running = False


class PostJob(ParallelJob):

    def __init__(self, channel: Channel, short_text: bool = True) -> None:
        super().__init__(channel.interval, None)
        self.channel: Channel = channel
        self.account: Account = Account.get(channel.owner_id)
        self.short_text = short_text

    def do(self, postman: PostMan, send_message_func: Callable[..., any], call_time: int) -> bool:
        """This job's function is obvious(sending post in channel via bot instance)"""
        if not self.account.is_member_plus() or not self.running:
            return False  # False means that postjob is running but it doesnt have run permission because of
        post_body = postman.create_post(self.account, self.channel, short_text=self.short_text)
        self.last_run_result = send_message_func(chat_id=self.channel.id, text=post_body)
        self.last_call_time = call_time
        return True
