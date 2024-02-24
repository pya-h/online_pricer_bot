from db.account import Account
from tools.mathematix import tz_today
from plus.db.interface import DatabasePlusInterface
from datetime import datetime
from tools.exceptions import NotPlusException
from enum import Enum
from plus.models.plusplan import PlusPlan
from plus.models.channel import Channel


class UserStates(Enum):
    NONE = 0
    SELECT_CHANNEL = 4
    SELECT_INTERVAL = 5

class AccountPlus(Account):

    MaxSelectionInDesiredOnes = 100
    _database = None

    @staticmethod
    def Database():
        if AccountPlus._database == None:
            AccountPlus._database = DatabasePlusInterface.Get()
        return AccountPlus._database

    def __init__(self, chat_id: int, currencies: list=None, cryptos: list=None, language: str = 'fa', plus_end_date: datetime = None, plus_plan_id: int = 0) -> None:
        super().__init__(chat_id, currencies, cryptos, language)
        self.state: UserStates = UserStates.NONE
        self.plus_end_date = plus_end_date
        self.plus_plan_id= plus_plan_id
        # self.channels: Dict[Channel] = dict()  # TODO: Load this from DATABASE

    def max_channel_plans(self):
        # decide with plus_plan_id
        return 3

    def my_channel_plans(self) -> list[Channel]:
        return list(filter(lambda channel: channel.owner_id == self.chat_id, Channel.Instances.values()))

    @staticmethod
    def Get(chat_id):
        if chat_id in AccountPlus.Instances:
            AccountPlus.Instances[chat_id].last_interaction = tz_today()
            return AccountPlus.Instances[chat_id]
        row = AccountPlus.Database().get(chat_id)
        if row:
            currs = row[1] if not row[1] or row[1][-1] != ";" else row[1][:-1]
            cryptos = row[2] if not row[2] or row[2][-1] != ";" else row[2][:-1]
            plus_end_date = datetime.strptime(row[4], DatabasePlusInterface.DATE_FORMAT) if row[4] else None
            try:
                plus_plan_id= int(row[5])
            except:
                plus_plan_id= 0
            language = row[-1]
            return AccountPlus(chat_id=int(row[0]), currencies=currs.split(";") if currs else None, cryptos=cryptos.split(';') if cryptos else None, plus_end_date=plus_end_date, plus_plan_id=plus_plan_id, language=language)

        return AccountPlus(chat_id=chat_id).save()

    def is_member_plus(self) -> bool:
        '''Check if the account has still plus subscription.'''
        return self.plus_end_date is not None and tz_today().date() <= self.plus_end_date.date() and self.plus_plan_id

    def plan_new_channel(self, channel_id: int, interval: int, channel_name: str, channel_title: str = None) -> Channel:
        if not self.is_member_plus():
            raise NotPlusException(self.chat_id)
        channel = Channel(self.chat_id, channel_id, interval, channel_name=channel_name, channel_title=channel_title)
        if channel.plan():
            # self.channels[channel_id] = channel
            return channel
        return None

    @staticmethod
    def Everybody():
        return AccountPlus.Database().get_all()


    def __del__(self):
        self.save()

    @staticmethod
    def GarbageCollect():
        now = tz_today()
        garbage = []
        for chat_id in AccountPlus.Instances:
            if (now - AccountPlus.Instances[chat_id].last_interaction).total_seconds() / 60 >= AccountPlus.GarbageCollectionInterval / 2:
                garbage.append(chat_id)
        # because changing dict size in a loop on itself causes error,
        # we first collect redundant chat_id s and then delete them from the memory
        for g in garbage:
            del AccountPlus.Instances[g]

    def updgrade(self, plus_plan_id):
        plus_plan = PlusPlan.Get(plus_plan_id)
        AccountPlus.Database().upgrade_account(self, plus_plan=plus_plan)
        