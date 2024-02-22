from payagraph.bot import TelegramBot
from payagraph.keyboards import Keyboard
from api.post import VIPPostManager
from typing import Dict
from payagraph.job import ParallelJob
from db.vip_models import Channel, VIPAccount
from payagraph.containers import TelegramMessage
from payagraph.keyboards import InlineKey, InlineKeyboard


class PostJob(ParallelJob):

    def __init__(self, channel: Channel, short_text: bool=True) -> None:
        super().__init__(channel.interval, None)
        self.channel: Channel = channel
        self.account: VIPAccount = VIPAccount.Get(channel.owner_id)
        self.short_text = short_text

    def do(self, bot: TelegramBot, call_time: int):
        '''This job's function is obvious(sending post in channel via bot instance)'''
        post_body = bot.post_manager.create_post(self.account, self.channel, short_text=self.short_text)
        message = TelegramMessage.Text(self.channel.id, post_body)
        self.last_run_result = bot.send(message)
        self.last_call_time = call_time


class TelegramBotPlus(TelegramBot):
    '''Specialized bot for online_pricer_vip bot'''
    def __init__(self, token: str, username: str, host_url: str, text_resources: dict,
                 _main_keyboard: Dict[str, Keyboard] | Keyboard = None, post_manager=None) -> None:
        super().__init__(token, username, host_url, text_resources, _main_keyboard)
        self.set_post_managers(post_manager)
        self.post_jobs: Dict[int, PostJob] = dict()

    def set_post_managers(self, post_manager: VIPPostManager):
        self.post_manager = post_manager

    def prepare_new_post_job(self, channel: Channel, short_text: bool=True):
        post_job = PostJob(channel=channel, short_text=short_text)
        self.post_jobs[channel.id] = post_job.go()

    def ticktock(self):
        now = super().ticktock()

        for id in self.post_jobs:
            if (self.post_jobs[id].running) and (now - self.post_jobs[id].last_call_time >= self.post_jobs[id].interval):
                self.post_jobs[id].do(self, now)

    def cancel_postjob(self, channel_id: int):
        self.post_jobs[channel_id].stop()
        del self.post_jobs[channel_id]

    # Parallel Jovbs:
    def load_channels_and_plans(self):
        '''Load all channels saved in the database (with plans[interval > 0]) and prepare their postjobs'''
        for channel_id in Channel.GetHasPlanChannels():
            if channel_id: # and channel.interval > 0:
                self.prepare_new_post_job(Channel.Instances[channel_id], short_text=True) # Check short text

    def keyboard_with_back_key(self, language, *rows) -> Keyboard:
        return Keyboard(*rows, [self.keyword("main_menu", language)])

