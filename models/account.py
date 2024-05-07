from decouple import config
from db.interface import *
from datetime import datetime, date
from tools.mathematix import tz_today, now_in_minute, from_now_time_diff
from tools.manuwriter import log
from enum import Enum
from models.channel import Channel
from models.plusplan import PlusPlan


ADMIN_USERNAME = config('ADMIN_USERNAME')
ADMIN_PASSWORD = config('ADMIN_PASSWORD')

class UserStates(Enum):
    NONE = 0
    SEND_POST = 1
    INPUT_EQUALIZER_AMOUNT = 2
    INPUT_EQUALIZER_UNIT = 3
    SELECT_CHANNEL = 4
    SELECT_INTERVAL = 5
    SELECT_LANGUAGE = 6
    CONFIG_BAZAARS = 7

class Account:
    # states:

    _database = None
    GarbageCollectionInterval = 30
    PreviousGarbageCollectionTime: int = now_in_minute() # in minutes
    Instances = {}  # active accounts will cache into this; so there's no need to access database everytime
    # causing a slight enhancement on performance
    @staticmethod
    def Database():
        if Account._database == None:
            Account._database = DatabaseInterface.Get()
        return Account._database

    def no_interaction_duration(self):
        diff, _ =  from_now_time_diff(self.last_interaction)
        return diff

    @staticmethod
    def GarbageCollect():
        now = now_in_minute()
        if now - Account.PreviousGarbageCollectionTime <= Account.GarbageCollectionInterval:
            return

        garbage = []
        Account.PreviousGarbageCollectionTime = now
        for chat_id in Account.Instances:
            if Account.Instances[chat_id].no_interaction_duration() >= Account.GarbageCollectionInterval / 2:
                garbage.append(chat_id)
        # because changing dict size in a loop on itself causes error,
        # we first collect redundant chat_id s and then delete them from the memory
        cleaned_counts = len(garbage)
        for g in garbage:
            del Account.Instances[g]

        log(f"Cleaned {cleaned_counts} accounts from my simple cache store.", category_name="account_gc")

    @staticmethod
    def Get(chat_id):
        Account.GarbageCollect()
        if chat_id in Account.Instances:
            Account.Instances[chat_id].last_interaction = tz_today()
            return Account.Instances[chat_id]
        row = Account.Database().get(chat_id)
        if row:
            currs = row[1] if not row[1] or row[1][-1] != ";" else row[1][:-1]
            cryptos = row[2] if not row[2] or row[2][-1] != ";" else row[2][:-1]
            return Account(int(row[0]), currs.split(";") if currs else None, cryptos.split(';') if cryptos else None)

        return Account(chat_id=chat_id).save()

    @staticmethod
    def Everybody():
        return Account.Database().get_all()

    def save(self):
        self.Database().update(self)
        return self

    def __del__(self):
        self.save()

    def arrange_instances(self):
        Account.GarbageCollect()
        Account.Instances[self.chat_id] = self

    def __init__(self, chat_id, currencies=None, cryptos=None, language: str='fa', 
                 plus_end_date: datetime = None, plus_plan_id: int = 0, state: UserStates = UserStates.NONE, cache = None) -> None:
        self.is_admin: bool = False
        self.chat_id: int = chat_id
        self.desired_coins: list = cryptos if cryptos else []
        self.desired_currencies: list = currencies if currencies else []
        self.last_interaction: datetime = tz_today()
        self.language: str = language
        self.state: UserStates = state
        self.cache = cache
        self.plus_end_date = plus_end_date
        self.plus_plan_id = plus_plan_id
        self.desires_count_max = 20  #FIXME: update this with plus plan
        self.username: str = None
        self.firstname: str = None
        self.arrange_instances()

    def change_state(self, state: UserStates = UserStates.NONE, data: any = None):
        self.state = state
        self.state_data = data

    def __str__(self) -> str:
        return f'{self.chat_id}'

    def authorization(self, args):
        if self.is_admin:
            return True

        if args and len(args) >= 2:
            username = args[0]
            password = args[1]
            self.is_admin = password == ADMIN_PASSWORD and username == ADMIN_USERNAME
            return self.is_admin

        return False

    def str_desired_coins(self):
        return ';'.join(self.desired_coins)

    def str_desired_currencies(self):
        return ';'.join(self.desired_currencies)

    def set_extra_info(self, firstname: str, username: str = None) -> None:
        '''This extra infos are just for temprory messaging purposes and wont be saved in database.'''
        self.firstname = firstname
        self.username = username


    def max_channel_plans(self):
        # decide with plus_plan_id
        return 3

    def my_channel_plans(self) -> list[Channel]:
        return list(filter(lambda channel: channel.owner_id == self.chat_id, Channel.Instances.values()))

    @staticmethod
    def Get(chat_id):
        if chat_id in Account.Instances:
            Account.Instances[chat_id].last_interaction = tz_today()
            return Account.Instances[chat_id]
        row = Account.Database().get(chat_id)
        if row:
            currs = row[1] if not row[1] or row[1][-1] != ";" else row[1][:-1]
            cryptos = row[2] if not row[2] or row[2][-1] != ";" else row[2][:-1]
            plus_end_date = datetime.strptime(row[4], DatabaseInterface.DATE_FORMAT) if row[4] else None
            try:
                plus_plan_id= int(row[5])
            except:
                plus_plan_id= 0
            state = row[6]
            cache = row[7]
            language = row[-1]
            return Account(chat_id=int(row[0]), currencies=currs.split(";") if currs else None,
                        cryptos=cryptos.split(';') if cryptos else None, plus_end_date=plus_end_date, 
                        plus_plan_id=plus_plan_id, language=language, state=state, cache=cache)

        return Account(chat_id=chat_id).save()

    def is_member_plus(self) -> bool:
        '''Check if the account has still plus subscription.'''
        return self.plus_end_date is not None and tz_today().date() <= self.plus_end_date.date() and self.plus_plan_id

    def plan_new_channel(self, channel_id: int, interval: int, channel_name: str, channel_title: str = None) -> Channel:
        channel = Channel(self.chat_id, channel_id, interval, channel_name=channel_name, channel_title=channel_title)
        if channel.plan():
            # self.channels[channel_id] = channel
            return channel
        return None
    def updgrade(self, plus_plan_id):
        plus_plan = PlusPlan.Get(plus_plan_id)
        Account.Database().upgrade_account(self, plus_plan=plus_plan)
        
    @staticmethod
    def Everybody():
        return Account.Database().get_all()

    def save(self):
        self.Database().update(self)
        return self

    def __del__(self):
        self.save()

    @staticmethod
    def Statistics():
        # first save all last interactions:
        for id in Account.Instances:
            Account.Instances[id].save()
        now = tz_today().date()
        today_actives, yesterday_actives, this_week_actives, this_month_actives = 0, 0, 0, 0

        last_interactions = Account.Database().get_all(column=DatabaseInterface.ACCOUNT_LAST_INTERACTION)
        for interaction_date in last_interactions:
            if interaction_date and (isinstance(interaction_date, datetime) or isinstance(interaction_date, date)):
                if now.year == interaction_date.year:
                    if now.month == interaction_date.month:
                        this_month_actives += 1
                        if now.isocalendar()[1] == interaction_date.isocalendar()[1]:
                            this_week_actives += 1
                            if now.day == interaction_date.day:
                                today_actives += 1
                        if now.day == interaction_date.day + 1:
                            yesterday_actives += 1
                    elif now.month == interaction_date.month + 1:
                        delta = now - (interaction_date.date() if isinstance(interaction_date, datetime) else interaction_date)
                        if delta and delta.days == 1:
                            yesterday_actives += 1
                elif now.year == interaction_date.year + 1 and now.month == 1 and interaction_date.month == 12:
                        delta = now - (interaction_date.date() if isinstance(interaction_date, datetime) else interaction_date)
                        if delta and delta.days == 1:
                            yesterday_actives += 1
        return {'daily': today_actives, 'yesterday': yesterday_actives, 'weekly': this_week_actives, 'monthly': this_month_actives, 'all': len(last_interactions)}
