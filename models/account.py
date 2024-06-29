from decouple import config
from db.interface import *
from datetime import datetime, date
from tools.mathematix import tz_today, now_in_minute, from_now_time_diff
from tools.manuwriter import log
from enum import Enum
from models.channel import Channel
from typing import List, Dict
from bot.types import SelectionListTypes, MarketOptions
from json import loads as json_parse, dumps as jsonify
from models.alarms import PriceAlarm
from telegram import Chat


ADMIN_USERNAME = config('ADMIN_USERNAME')
ADMIN_PASSWORD = config('ADMIN_PASSWORD')
HARDCODE_ADMIN_USERNAME = config('HARDCODE_ADMIN_USERNAME', 'pya_h')
HARDCODE_ADMIN_CHATID = int(config('HARDCODE_ADMIN_CHATID', 0))


class Account:
    # states:
    class States(Enum):
        NONE = 0
        SEND_POST = 1
        INPUT_EQUALIZER_AMOUNT = 2
        INPUT_EQUALIZER_UNIT = 3
        SELECT_CHANNEL = 4
        SELECT_INTERVAL = 5
        SELECT_LANGUAGE = 6
        CONFIG_MARKETS = 7
        CONFIG_CALCULATOR_LIST = 8
        CREATE_ALARM = 9
        UPGRADE_USER = 10

        @staticmethod
        def Which(value: int):
            values = (
                Account.States.NONE,
                Account.States.SEND_POST,
                Account.States.INPUT_EQUALIZER_AMOUNT,
                Account.States.INPUT_EQUALIZER_UNIT,
                Account.States.SELECT_CHANNEL,
                Account.States.SELECT_INTERVAL,
                Account.States.SELECT_LANGUAGE,
                Account.States.CONFIG_MARKETS,
                Account.States.CONFIG_CALCULATOR_LIST,
                Account.States.CREATE_ALARM,
            )
            try:
                return values[int(value)]
            except:
                pass
            return Account.States.NONE

    _database = None
    GarbageCollectionInterval = 30
    PreviousGarbageCollectionTime: int = now_in_minute()  # in minutes
    Instances: dict = {}  # active accounts will cache into this; so there's no need to access database everytime


    def no_interaction_duration(self):
        diff, _ = from_now_time_diff(self.last_interaction)
        return diff

    def arrange_instances(self):
        Account.GarbageCollect()
        Account.Instances[self.chat_id] = self

    def __init__(self, chat_id, currencies: List[str] = None, cryptos: List[str] = None, calc_cryptos: List[str] = None,
                 calc_currencies: List[str] = None, language: str = 'fa', plus_end_date: datetime = None,
                 state: States = States.NONE, cache=None, is_admin: bool = False, username: str | None = None,
                 prevent_instance_arrangement: bool = False, ) -> None:

        self.chat_id: int = chat_id
        self.desired_cryptos: list = cryptos if cryptos else []
        self.desired_currencies: list = currencies if currencies else []
        self.calc_cryptos: list = calc_cryptos if calc_cryptos else []
        self.calc_currencies: list = calc_currencies if calc_currencies else []
        self.last_interaction: datetime = tz_today()
        self.language: str = language
        self.state: Account.States = state
        self.cache: Dict[str, any] = cache or {}
        self.plus_end_date = plus_end_date
        self.username: str | None = username[1:] if username and (username[0] == '@') else username
        self.firstname: str | None = None
        self.is_admin: bool = is_admin or (self.chat_id == HARDCODE_ADMIN_CHATID)
        if not prevent_instance_arrangement:
            self.arrange_instances()

    def change_state(self, state: States = States.NONE, cache_key: str = None, data: any = None, clear_cache: bool = False):
        self.state = state
        self.add_cache(cache_key, data, clear_cache)

    def add_cache(self, cache_key: str = None, data: any = None, clear_cache: bool = False):
        if clear_cache:
            self.clear_cache()
        if cache_key:
            self.cache[cache_key] = data

    def delete_specific_cache(self, *keys):
        keys = list(keys)
        for key in keys:
            if key in self.cache:
                del self.cache[key]

    def clear_cache(self):
        self.cache.clear()

    def get_cache(self, cache_key: str = None):
        return self.cache[cache_key] if cache_key in self.cache else None

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

    def str_desired_cryptos(self):
        return ';'.join(self.desired_cryptos)

    def str_desired_currencies(self):
        return ';'.join(self.desired_currencies)

    def str_calc_cryptos(self):
        return ';'.join(self.calc_cryptos)

    def str_calc_currencies(self):
        return ';'.join(self.calc_currencies)

    def set_extra_info(self, firstname: str, username: str = None) -> None:
        """This extra info are just for temporary messaging purposes and won't be saved in database."""
        self.firstname = firstname
        self.username = username

    def my_channel_plans(self) -> list[Channel]:
        return list(filter(lambda channel: channel.owner_id == self.chat_id, Channel.Instances.values()))

    
    def is_premium_member(self) -> bool:
        """Check if the account has still plus subscription."""
        return self.is_admin or (
                    self.plus_end_date is not None and tz_today().date() <= self.plus_end_date.date())

    def plan_new_channel(self, channel_id: int, interval: int, channel_name: str,
                         channel_title: str = None) -> Channel | None:
        channel = Channel(self.chat_id, channel_id, interval, channel_name=channel_name, channel_title=channel_title)
        if channel.plan():
            # self.channels[channel_id] = channel
            return channel
        return None

    def upgrade(self, duration_in_months: int):
        Account.Database().upgrade_account(self, duration_in_months)

    def cache_as_str(self) -> str | None:
        return jsonify(self.cache) if self.cache else None

    def save(self):
        self.Database().update(self)
        return self

    def __del__(self):
        self.save()

    def handle_market_selection(self, list_type: SelectionListTypes, market: MarketOptions, symbol: str | None = None):
        target_list: List[str]
        related_list: List[str]

        match list_type:
            case SelectionListTypes.CALCULATOR:
                (target_list, related_list) = (
                    self.calc_cryptos, self.calc_currencies) if market == MarketOptions.CRYPTO else (
                    self.calc_currencies, self.calc_cryptos)
            case SelectionListTypes.FOLLOWING:
                (target_list, related_list) = (
                    self.desired_cryptos, self.desired_currencies) if market == MarketOptions.CRYPTO else (
                    self.desired_currencies, self.desired_cryptos)
            
            case SelectionListTypes.ALARM | SelectionListTypes.EQUALIZER_UNIT:
                return None
            case _:
                raise ValueError(f'Invalid list type selected by: {self.state.value}')

        if symbol:
            if symbol.upper() not in target_list:
                if len(target_list) + len(related_list) >= self.max_selection_count:
                    raise ValueError(self.max_selection_count)

                target_list.append(symbol)
                self.save()
            else:
                target_list.remove(symbol)
        return target_list

    def match_state_with_selection_type(self):
        match self.state:
            case Account.States.CONFIG_MARKETS:
                return SelectionListTypes.FOLLOWING
            case Account.States.INPUT_EQUALIZER_UNIT:
                return SelectionListTypes.EQUALIZER_UNIT
            case Account.States.CONFIG_CALCULATOR_LIST:
                return SelectionListTypes.CALCULATOR
            case Account.States.CREATE_ALARM:
                return SelectionListTypes.ALARM
        return None

    def get_alarms(self) -> List[PriceAlarm]:
        return PriceAlarm.GetByUser(self.chat_id)

    def factory_reset(self):
        self.desired_cryptos = ''
        self.desired_currencies = ''
        self.calc_cryptos = ''
        self.calc_currencies = ''
        self.language = 'fa'
        self.clear_cache()
        self.state = Account.States.NONE
        self.save()

        # disable(delete) all alarms
        for alarm in self.get_alarms():
            alarm.disable()

        # stop(delete) all planned channels
        for channel in self.get_planned_channels():
            channel.stop_plan()
    
    def get_planned_channels(self) -> List[Channel]:
        return Channel.GetByOwner(self.chat_id)
    
    @property.setter
    def current_username(self, username: str):
        if not username:
            return
        if username[0] == '@':
            username = username[1:]
        if username != self.username:
            self.username = username
            self.Database().update_username(self)

    @property
    def alarms_count(self):
        return self.Database().get_number_of_user_alarms(self.chat_id)
    
    @property
    def can_create_new_alarm(self):
        return self.alarms_count < self.max_alarms_count
    
    # user privileges:
    @property
    def max_selection_count(self):
        if self.is_premium_member():
            return 100
        return 10
    
    @property
    def max_alarms_count(self):
        if self.is_premium_member():
            return 10
        return 3

    @property
    def max_channel_plans_count(self):
        if self.is_premium_member():
            return 1
        return 0
    
        # causing a slight enhancement on performance

    @staticmethod
    def Database():
        if Account._database is None:
            Account._database = DatabaseInterface.Get()
        return Account._database


    @staticmethod
    def str2list(string: str):
        return string.split(';') if string else None

    @staticmethod
    def list2str(lst: List[str]):
        return ';'.join(lst)

    @staticmethod
    def ExtractQueryRowData(row: tuple, prevent_instance_arrangement: bool = False):
        def xstr(r):
            return r if not r or r[-1] != ";" else r[:-1]

        currs = xstr(row[1])
        cryptos = xstr(row[2])
        calc_currs = xstr(row[3])
        calc_cryptos = xstr(row[4])

        username = row[5]
        # add new rows here

        plus_end_date = datetime.strptime(row[-5], DatabaseInterface.DATE_FORMAT) if row[-5] else None
        state = Account.States.Which(row[-4])
        cache = Account.load_cache(row[-3])
        is_admin = row[-2]
        language = row[-1]
        return Account(chat_id=int(row[0]), currencies=Account.str2list(currs), cryptos=Account.str2list(cryptos),
                       plus_end_date=plus_end_date, calc_currencies=Account.str2list(calc_currs),
                       calc_cryptos=Account.str2list(calc_cryptos), is_admin=is_admin, username=username,
                       language=language, state=state, cache=cache, prevent_instance_arrangement=prevent_instance_arrangement)

    @staticmethod
    def Get(chat: Chat, prevent_instance_arrangement: bool = False):
        account = Account.GetById(chat.id, prevent_instance_arrangement=prevent_instance_arrangement)
        account.current_username = chat.username
        return account
    
    @staticmethod
    def GetById(chat_id: int, prevent_instance_arrangement: bool = False):
        if chat_id in Account.Instances:
            account: Account = Account.Instances[chat_id]
            account.last_interaction = tz_today()
            return account
        
        row = Account.Database().get(chat_id)
        if row:
            account = Account.ExtractQueryRowData(row, prevent_instance_arrangement=prevent_instance_arrangement)
            return account

        return Account(chat_id=chat_id, prevent_instance_arrangement=prevent_instance_arrangement).save()

    @staticmethod
    def GetByUsername(username: str):
        if not username:
            return None
        if username[0] == '@':
            username = username[1:]
        accounts = filter(lambda acc: acc.username == username, list(Account.Instances.values()))
        if accounts:
            return accounts[0]

        accounts = Account.Database().get_special_accounts(DatabaseInterface.ACCOUNT_USERNAME, username)
        if accounts:
            return Account.ExtractQueryRowData(accounts[0])
        return None

    @staticmethod
    def GetHardcodeAdmin():
        return {'id': HARDCODE_ADMIN_CHATID, 'username': HARDCODE_ADMIN_USERNAME,
                'account': Account.GetById(HARDCODE_ADMIN_CHATID)}

    @staticmethod
    def load_cache(data_string: str | None):
        return json_parse(data_string) if data_string else {}

    @staticmethod
    def Everybody():
        return Account.Database().get_all()

    @staticmethod
    def Statistics():
        # first save all last interactions:
        for kid in Account.Instances:
            Account.Instances[kid].save()
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
                        delta = now - (
                            interaction_date.date() if isinstance(interaction_date, datetime) else interaction_date)
                        if delta and delta.days == 1:
                            yesterday_actives += 1
                elif now.year == interaction_date.year + 1 and now.month == 1 and interaction_date.month == 12:
                    delta = now - (
                        interaction_date.date() if isinstance(interaction_date, datetime) else interaction_date)
                    if delta and delta.days == 1:
                        yesterday_actives += 1
        return {'daily': today_actives, 'yesterday': yesterday_actives, 'weekly': this_week_actives,
                'monthly': this_month_actives, 'all': len(last_interactions)}

    @staticmethod
    def GetAdmins(just_hardcode_admin: bool = True):
        if not just_hardcode_admin:
            admins = list(
                map(lambda data: Account.ExtractQueryRowData(data), Account.Database().get_special_accounts()))
            if HARDCODE_ADMIN_CHATID:
                admins.insert(0, Account.GetHardcodeAdmin()['account'])
            return admins
        return [Account.GetHardcodeAdmin()['account'], ]

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
