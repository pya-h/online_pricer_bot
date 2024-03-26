from payagraph.bot import TelegramBot
from payagraph.keyboards import Keyboard
from plus.services.post import PostServicePlus
from typing import Dict
from payagraph.job import ParallelJob
from plus.models.account import AccountPlus
from plus.models.channel import Channel
from payagraph.containers import GenericMessage
from plus.gateway.order import Order
from plus.gateway.nowpayments import NowpaymentsGateway
from plus.models.plusplan import PlusPlan
import json
from payagraph.keyboards import InlineKey, InlineKeyboard


class PostJob(ParallelJob):

    def __init__(self, channel: Channel, short_text: bool=True) -> None:
        super().__init__(channel.interval, None)
        self.channel: Channel = channel
        self.account: AccountPlus = AccountPlus.Get(channel.owner_id)
        self.short_text = short_text

    def do(self, bot: TelegramBot, call_time: int) -> bool:
        '''This job's function is obvious(sending post in channel via bot instance)'''
        if not self.account.is_member_plus() or not self.running:
            return False # False means that postjob is running but it doesnt have run permission because of
        post_body = bot.post_service.create_post(self.account, self.channel, short_text=self.short_text)
        message = GenericMessage.Text(self.channel.id, post_body)
        self.last_run_result = bot.send(message)
        self.last_call_time = call_time
        return True


class TelegramBotPlus(TelegramBot):
    '''Specialized bot for online_pricer_plus bot'''
    def __init__(self, token: str, username: str, host_url: str, text_resources: dict,
                 _main_keyboard: Dict[str, Keyboard] | Keyboard = None, post_service: PostServicePlus=None) -> None:
        super().__init__(token, username, host_url, text_resources, _main_keyboard)
        self.post_service: PostServicePlus = post_service
        self.post_jobs: Dict[int, PostJob] = dict()

    def set_post_services(self, post_service: PostServicePlus):
        self.post_service: PostServicePlus = post_service

    def prepare_new_post_job(self, channel: Channel, short_text: bool=True):
        post_job = PostJob(channel=channel, short_text=short_text)
        self.post_jobs[channel.id] = post_job.go()

    def ticktock(self):
        now = super().ticktock()
        redundants = []

        for id in self.post_jobs:
            if (self.post_jobs[id].running) and (now - self.post_jobs[id].last_call_time >= self.post_jobs[id].interval):
                if not self.post_jobs[id].do(self, now): # run the post job, if it wasnt allowed to run (user easnt member plud)
                    redundants.append(id)

        for job_id in redundants:
            del self.post_jobs[job_id]


        # if there was any job that its owner plus membership is over then:
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


    def list_all_plans(self, lang="fa"):
        plans = PlusPlan.PlusPlansList()
        lang = lang.lower()
        if not plans or not len(plans):
            return None
        rows = list(map(
            lambda plan: InlineKey(plan.short_description(lang), callback_data=json.dumps({"a": "buy+plan", "v": plan.id})), plans)
        )
        return InlineKeyboard(*rows)
