from decouple import config
from db.interface import *
from datetime import datetime, date
from tools.mathematix import tz_today, now_in_minute, from_now_time_diff
from tools.manuwriter import log
from enum import Enum
from models.channel import Channel
from models.group import Group
from typing import List, Dict
from bot.types import SelectionListTypes, MarketOptions
from json import loads as json_parse, dumps as jsonify
from telegram import Chat, User
from tools.exceptions import NoSuchThingException


ADMIN_USERNAME = config("ADMIN_USERNAME")
ADMIN_PASSWORD = config("ADMIN_PASSWORD")
HARDCODE_ADMIN_USERNAME = config("HARDCODE_ADMIN_USERNAME", "pya_h")
HARDCODE_ADMIN_CHATID = int(config("HARDCODE_ADMIN_CHATID", 0))


class Account:
    # states:
    class States(Enum):
        NONE = 0
        SEND_POST = 1
        INPUT_EQUALIZER_AMOUNT = 2
        INPUT_EQUALIZER_UNIT = 3
        CONFIG_MARKETS = 4
        CONFIG_CALCULATOR_LIST = 5
        CREATE_ALARM = 6
        UPGRADE_USER = 7
        DOWNGRADE_USER = 8
        ADD_BOT_AS_ADMIN = 9
        SELECT_POST_INTERVAL = 10
        CHANGE_POST_INTERVAL = 11
        CONFIG_GROUP_MARKETS = 12
        CONFIG_CHANNEL_MARKETS = 13
        SET_MESSAGE_FOOTER = 14
        SET_MESSAGE_HEADER = 15
        CHANGE_GROUP = 16
        CHNAGE_CHANNEL = 17

        @staticmethod
        def Which(value: int):
            try:
                return Account.UserStates[int(value)]
            except:
                pass
            return Account.States.NONE

    UserStates = (
        States.NONE,
        States.SEND_POST,
        States.INPUT_EQUALIZER_AMOUNT,
        States.INPUT_EQUALIZER_UNIT,
        States.CONFIG_MARKETS,
        States.CONFIG_CALCULATOR_LIST,
        States.CREATE_ALARM,
        States.UPGRADE_USER,
        States.DOWNGRADE_USER,
        States.ADD_BOT_AS_ADMIN,
        States.SELECT_POST_INTERVAL,
        States.CHANGE_POST_INTERVAL,
        States.CONFIG_GROUP_MARKETS,
        States.CONFIG_CHANNEL_MARKETS,
        States.SET_MESSAGE_FOOTER,
        States.SET_MESSAGE_HEADER,
        States.CHANGE_GROUP,
        States.CHNAGE_CHANNEL,
    )

    _database = None
    FastMemGarbageCollectionInterval = 5
    PreviousFastMemGarbageCollectionTime: int = now_in_minute()  # in minutes
    FastMemInstances: dict = {}  # active accounts will cache into this; so there's no need to access database every time

    def no_interaction_duration(self):
        diff, _ = from_now_time_diff(self.last_interaction)
        return diff

    def organize_fastmem(self):
        Account.GarbageCollect()
        Account.FastMemInstances[self.chat_id] = self

    def __init__(
        self,
        chat_id: int,
        currencies: List[str] = None,
        cryptos: List[str] = None,
        calc_cryptos: List[str] = None,
        calc_currencies: List[str] = None,
        language: str = "fa",
        plus_end_date: datetime = None,
        state: States = States.NONE,
        cache=None,
        is_admin: bool = False,
        username: str | None = None,
        no_fastmem: bool = False,
    ) -> None:

        self.chat_id: int = int(chat_id)
        self.desired_cryptos: list = cryptos or []
        self.desired_currencies: list = currencies or []
        self.calc_cryptos: list = calc_cryptos or []
        self.calc_currencies: list = calc_currencies or []
        self.last_interaction: datetime = tz_today()
        self.language: str = language
        self.state: Account.States = state
        self.cache: Dict[str, any] = cache or {}
        self.plus_end_date = plus_end_date
        self.username: str | None = username[1:] if username and (username[0] == "@") else username
        self.firstname: str | None = None
        self.is_admin: bool = is_admin or (self.chat_id == HARDCODE_ADMIN_CHATID)
        if not no_fastmem:
            self.organize_fastmem()

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
        return f"{self.username if self.username else self.chat_id}"

    def authorization(self, args):
        if self.is_admin:
            return True

        if args and len(args) >= 2:
            username = args[0]
            password = args[1]
            self.is_admin = password == ADMIN_PASSWORD and username == ADMIN_USERNAME
            return self.is_admin

        return False

    @property
    def desired_cryptos_as_str(self):
        return ";".join(self.desired_cryptos)

    @property
    def desired_currencies_as_str(self):
        return ";".join(self.desired_currencies)

    @property
    def calc_cryptos_as_str(self):
        return ";".join(self.calc_cryptos)

    @property
    def calc_currencies_as_str(self):
        return ";".join(self.calc_currencies)

    def set_extra_info(self, firstname: str, username: str = None) -> None:
        """This extra info are just for temporary messaging purposes and won't be saved in database."""
        self.firstname = firstname
        self.username = username

    @property
    def is_premium(self) -> bool:
        """Check if the account has still plus subscription."""
        return self.is_admin or ((self.plus_end_date is not None) and (tz_today().date() <= self.plus_end_date.date()))

    def upgrade(self, duration_in_months: int):
        Account.Database().upgrade_account(self, duration_in_months)

    def downgrade(self):
        Account.Database().downgrade_account(self)

    @property
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
        save_func: callable = self.save

        match list_type:
            case SelectionListTypes.CALCULATOR:
                (target_list, related_list) = (
                    (self.calc_cryptos, self.calc_currencies)
                    if market == MarketOptions.CRYPTO
                    else (self.calc_currencies, self.calc_cryptos)
                )
            case SelectionListTypes.USER_TOKENS:
                (target_list, related_list) = (
                    (self.desired_cryptos, self.desired_currencies)
                    if market == MarketOptions.CRYPTO
                    else (self.desired_currencies, self.desired_cryptos)
                )
            case SelectionListTypes.GROUP_TOKENS:
                my_group = Group.GetByOwner(self.chat_id, take=1)
                if not my_group:
                    raise NoSuchThingException(self.chat_id, 'Group')
                (target_list, related_list) = (
                    (my_group.selected_coins, my_group.selected_currencies)
                    if market == MarketOptions.CRYPTO
                    else (my_group.selected_currencies, my_group.selected_coins)
                )
                save_func = my_group.save
            case SelectionListTypes.CHANNEL_TOKENS:
                my_channel = Channel.GetByOwner(self.chat_id, take=1)
                if not my_channel:
                    raise NoSuchThingException(self.chat_id, 'Channel')
                (target_list, related_list) = (
                    (my_channel.selected_coins, my_channel.selected_currencies)
                    if market == MarketOptions.CRYPTO
                    else (my_channel.selected_currencies, my_channel.selected_coins)
                )
                save_func = my_channel.save
            case SelectionListTypes.ALARM | SelectionListTypes.EQUALIZER_UNIT:
                return None
            case _:
                raise ValueError(f"Invalid list type selected by: {self.state.value}")

        if symbol:
            if symbol.upper() not in target_list:
                if len(target_list) + len(related_list) >= self.max_selection_count:
                    raise ValueError(self.max_selection_count)

                target_list.append(symbol)
            else:
                target_list.remove(symbol)
            save_func()
        return target_list

    def match_state_with_selection_type(self):
        match self.state:
            case Account.States.CONFIG_MARKETS:
                return SelectionListTypes.USER_TOKENS
            case Account.States.CONFIG_GROUP_MARKETS:
                return SelectionListTypes.GROUP_TOKENS
            case Account.States.CONFIG_CHANNEL_MARKETS:
                return SelectionListTypes.CHANNEL_TOKENS
            case Account.States.INPUT_EQUALIZER_UNIT:
                return SelectionListTypes.EQUALIZER_UNIT
            case Account.States.CONFIG_CALCULATOR_LIST:
                return SelectionListTypes.CALCULATOR
            case Account.States.CREATE_ALARM:
                return SelectionListTypes.ALARM
        return None

    def factory_reset(self):
        self.desired_cryptos = ""
        self.desired_currencies = ""
        self.calc_cryptos = ""
        self.calc_currencies = ""
        self.language = "fa"
        self.clear_cache()
        self.state = Account.States.NONE
        self.save()

        # disable(delete) all alarms
        for alarm in self.get_alarms():
            alarm.disable()

        # stop(delete) all planned channels
        for channel in self.get_planned_channels():
            channel.stop_plan()

        # FIXME: Also disable groups

    def get_planned_channels(self) -> List[Channel]:
        return Channel.GetByOwner(self.chat_id)

    @property
    def user_detail(self) -> str:
        detail = f'Telegram ID: {self.chat_id}\nUsername: {"@" + self.username if self.username else "-"}'
        if self.firstname:
            detail += f"\n{self.firstname}"
        return detail

    @staticmethod
    def GetPremiumUsers(from_date: datetime | None = None):
        rows = Account.Database().get_premium_accounts(from_date if from_date else datetime.now())
        return [Account.ExtractQueryRowData(row) for row in rows]

    @property
    def current_username(self):
        return self.username

    @current_username.setter
    def current_username(self, username: str):
        if not username:
            return
        if username[0] == "@":
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
        return 100 if self.is_premium else 10

    @property
    def max_alarms_count(self):
        return 10 if self.is_premium else 3

    @property
    def max_channel_count(self):
        return 1 if self.is_premium else 0

        # causing a slight enhancement on performance

    @property
    def my_channels_count(self) -> int:
        return self.Database().user_channels_count(self.chat_id)

    @property
    def has_channels(self) -> int:
        return bool(self.Database().get_user_channels(self.chat_id, take=1))

    @property
    def my_groups_count(self) -> int:
        return self.Database().user_groups_count(self.chat_id)

    @property
    def has_groups(self) -> int:
        return bool(self.Database().get_user_groups(self.chat_id, take=1))

    def get_my_groups(self):
        return Group.GetByOwner(self.chat_id)
    
    def get_my_channels(self):
        return Channel.GetByOwner(self.chat_id)

    @staticmethod
    def Database():
        if Account._database is None:
            Account._database = DatabaseInterface.Get()
        return Account._database

    @staticmethod
    def ExtractQueryRowData(row: tuple, no_fastmem: bool = False):
        currs = row[1]
        cryptos = row[2]
        calc_currs = row[3]
        calc_cryptos = row[4]

        username = row[5]
        # add new rows here

        plus_end_date = row[-5]
        state = Account.States.Which(row[-4])
        cache = Account.load_cache(row[-3])
        is_admin = row[-2]
        language = row[-1]
        return Account(
            chat_id=int(row[0]),
            currencies=DatabaseInterface.StringToList(currs),
            cryptos=DatabaseInterface.StringToList(cryptos),
            plus_end_date=plus_end_date,
            calc_currencies=DatabaseInterface.StringToList(calc_currs),
            calc_cryptos=DatabaseInterface.StringToList(calc_cryptos),
            is_admin=is_admin,
            username=username,
            language=language,
            state=state,
            cache=cache,
            no_fastmem=no_fastmem,
        )

    @staticmethod
    def Get(chat: Chat | User, no_fastmem: bool = False):
        account = Account.GetById(chat.id, no_fastmem=no_fastmem)
        account.current_username = chat.username
        account.firstname = (
            chat.first_name
        )  # It doesn't going to be saved in database, but its picked from Chat in case its needed in code.
        return account

    @staticmethod
    def GetById(chat_id: int, no_fastmem: bool = False):
        if chat_id in Account.FastMemInstances:
            account: Account = Account.FastMemInstances[chat_id]
            account.last_interaction = tz_today()
            return account

        row = Account.Database().get(chat_id)
        if row:
            account = Account.ExtractQueryRowData(row, no_fastmem=no_fastmem)
            return account

        return Account(chat_id=chat_id, no_fastmem=no_fastmem).save()

    @staticmethod
    def GetByUsername(username: str):
        if not username:
            return None
        if username[0] == "@":
            username = username[1:]
        accounts = list(filter(lambda acc: acc.username == username, list(Account.FastMemInstances.values())))
        if accounts:
            return accounts[0]

        accounts = Account.Database().get_special_accounts(DatabaseInterface.ACCOUNT_USERNAME, username)
        if accounts:
            return Account.ExtractQueryRowData(accounts[0])
        return None

    @staticmethod
    def GetHardcodeAdmin():
        return {
            "id": HARDCODE_ADMIN_CHATID,
            "username": HARDCODE_ADMIN_USERNAME,
            "account": Account.GetById(HARDCODE_ADMIN_CHATID),
        }

    @staticmethod
    def load_cache(data_string: str | None):
        return json_parse(data_string) if data_string else {}

    @staticmethod
    def Everybody():
        return Account.Database().get_all()

    @staticmethod
    def Statistics():
        # first save all last interactions:
        for kid in Account.FastMemInstances:
            Account.FastMemInstances[kid].save()
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
        return {
            "daily": today_actives,
            "yesterday": yesterday_actives,
            "weekly": this_week_actives,
            "monthly": this_month_actives,
            "all": len(last_interactions),
        }

    @staticmethod
    def GetAdmins(just_hardcode_admin: bool = True):
        if not just_hardcode_admin:
            admins = list(map(lambda data: Account.ExtractQueryRowData(data), Account.Database().get_special_accounts()))
            if HARDCODE_ADMIN_CHATID:
                admins.insert(0, Account.GetHardcodeAdmin()["account"])
            return admins
        return [
            Account.GetHardcodeAdmin()["account"],
        ]

    @staticmethod
    def GarbageCollect():
        now = now_in_minute()
        if now - Account.PreviousFastMemGarbageCollectionTime <= Account.FastMemGarbageCollectionInterval:
            return
        Account.PreviousFastMemGarbageCollectionTime = now
        interval_in_secs = Account.FastMemGarbageCollectionInterval * 60
        garbage = filter(
            lambda chat_id: Account.FastMemInstances[chat_id].no_interaction_duration() >= interval_in_secs,
            Account.FastMemInstances,
        )
        for g in garbage:
            Account.FastMemInstances[g].save()
            del Account.FastMemInstances[g]
