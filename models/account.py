from decouple import config
from db.interface import *
from datetime import datetime, date
from tools.mathematix import tz_today, now_in_minute, from_now_time_diff
from tools.manuwriter import log
from enum import Enum
from typing import List, Dict
from bot.types import SelectionListTypes
from json import loads as json_parse, dumps as jsonify
from telegram import Chat, User
from bot.settings import BotSettings
import gc
from api.crypto_service import CryptoCurrencyService
from api.currency_service import NavasanService


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
        SET_MESSAGE_FOOTNOTE = 14
        SET_MESSAGE_HEADER = 15
        CHANGE_GROUP = 16
        CHANGE_CHANNEL = 17
        ADMIN_CHANGE_PREMIUM_PLANS = 18

        @staticmethod
        def which(value: int):
            try:
                return Account.UserStates[int(value)]
            except:
                pass
            return Account.States.NONE

    class Modes(Enum):
        NORMAL = 0,
        ADMIN = 1,
        GOD = 2,

        @staticmethod
        def which(value: int):
            try:
                return Account.UserModes[int(value)]
            except:
                pass
            return Account.Modes.NORMAL

        @property
        def is_admin(self):
            return self.value != self.NORMAL.value

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
        States.SET_MESSAGE_FOOTNOTE,
        States.SET_MESSAGE_HEADER,
        States.CHANGE_GROUP,
        States.CHANGE_CHANNEL,
    )

    UserModes = (
        Modes.NORMAL,
        Modes.ADMIN,
        Modes.GOD
    )

    _database = None
    FastMemGarbageCollectionInterval = 5
    PreviousFastMemGarbageCollectionTime: int = now_in_minute()  # in minutes
    fastMemInstances: dict = (
        {}
    )  # active accounts will cache into this; so there's no need to access database every time
    botSettings: BotSettings | None = None

    def no_interaction_duration(self):
        diff, _ = from_now_time_diff(self.last_interaction)
        return diff

    def organize_fastmem(self):
        Account.garbageCollect()
        Account.fastMemInstances[self.chat_id] = self

    def __init__(
        self,
        chat_id: int,
        currencies: List[str] = None,
        cryptos: List[str] = None,
        calc_cryptos: List[str] = None,
        calc_currencies: List[str] = None,
        language: str = "fa",
        join_date: datetime = None,
        plus_start_date: datetime = None,
        plus_end_date: datetime = None,
        state: States = States.NONE,
        cache=None,
        mode: int | Modes = Modes.NORMAL,
        username: str | None = None,
        firstname: str | None = None,
        no_fastmem: bool = False,
    ) -> None:
        self.chat_id: int = int(chat_id)
        self.desired_cryptos: List[str] = cryptos or []
        self.desired_currencies: List[str] = currencies or []
        self.calc_cryptos: List[str] = calc_cryptos or []
        self.calc_currencies: List[str] = calc_currencies or []
        self.last_interaction: datetime = tz_today()
        self.language: str = language
        self.state: Account.States = state
        self.cache: Dict[str, any] = cache or {}
        self.join_date = join_date
        self.plus_start_date: datetime = plus_start_date
        self.plus_end_date: datetime = plus_end_date
        self.username: str | None = username[1:] if username and (username[0] == "@") else username
        self.firstname: str | None = firstname
        self.mode: Account.Modes = (mode if isinstance(mode, Account.Modes) else Account.Modes.which(mode))\
            if self.chat_id != HARDCODE_ADMIN_CHATID \
            else Account.Modes.GOD

        if not no_fastmem:
            self.organize_fastmem()

        if not Account.botSettings:
            Account.botSettings = BotSettings.get()

    def change_state(
        self, state: States = States.NONE, cache_key: str = None, data: any = None, clear_cache: bool = False
    ):
        self.state = state
        self.add_cache(cache_key, data, clear_cache)
        self.save()

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
        return f"@{self.username}" if self.username else str(self.chat_id)

    def authorization(self, args):
        if self.mode.is_admin:
            return True

        if args and len(args) >= 2:
            username = args[0]
            password = args[1]
            self.mode = Account.Modes.GOD if password == ADMIN_PASSWORD and username == ADMIN_USERNAME else Account.Modes.NORMAL
            self.save()
            return self.mode.is_admin

        return False

    def upgrade(self, duration_in_days: int):
        Account.database().upgrade_account(self, duration_in_days)

    def downgrade(self):
        Account.database().downgrade_account(self)

    @property
    def premium_date(self):
        return self.plus_end_date.date() if isinstance(self.plus_end_date, datetime) else self.plus_end_date

    @property
    def premium_days_remaining(self) -> int:
        try:
            if not self.plus_end_date:
                return -1
            delta = self.premium_date - tz_today().date()
            return delta.days
        except Exception as x:
            log(f"Failed to calculate remaining days of user premium plan, chat_id={self.chat_id}", "Premiums")
        return 0

    @property
    def desired_cryptos_as_str(self):
        return ";".join(self.desired_cryptos) if self.desired_cryptos else ""

    @property
    def desired_currencies_as_str(self):
        return ";".join(self.desired_currencies) if self.desired_currencies else ""

    @property
    def calc_cryptos_as_str(self):
        return ";".join(self.calc_cryptos) if self.calc_cryptos else ""

    @property
    def calc_currencies_as_str(self):
        return ";".join(self.calc_currencies) if self.calc_currencies else ""

    @property
    def is_premium(self) -> bool:
        """Check if the account has still plus subscription."""
        return self.mode or ((self.plus_end_date is not None) and (tz_today().date() <= self.plus_end_date.date()))

    @property
    def cache_as_str(self) -> str | None:
        return jsonify(self.cache) if self.cache else None

    def save(self):
        self.database().update_account(self)
        return self

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

    @property
    def user_detail(self) -> str:
        detail = f'Telegram ID: {self.chat_id}\nUsername: {"@" + self.username if self.username else "-"}'
        if self.firstname:
            detail += f"\nFirstname: {self.firstname}"
        if self.plus_end_date and (days := self.premium_days_remaining) >= 0:
            detail += f"\nPremium Days: {days}\n"
        return detail

    @property
    def name(self):
        return f"@{self.username}" if self.username else self.firstname

    @name.setter
    def name(self, chat: Chat):
        if not chat:
            return
        data_changed: bool = False
        username = chat.username
        if username and (username[0] == "@"):
            username = username[1:]
        if username != self.username:
            self.username = username
            data_changed = True
        if chat.first_name != self.firstname:
            self.firstname = chat.first_name
            data_changed = True

        if data_changed:
            self.database().update_account_names(self)

    @property
    def user_type(self) -> BotSettings.UserTypes:
        if self.mode:
            return BotSettings.UserTypes.ADMIN
        return BotSettings.UserTypes.FREE if not self.is_premium else BotSettings.UserTypes.PREMIUM

    @property
    def alarms_count(self):
        return self.database().get_number_of_user_alarms(self.chat_id)

    @property
    def can_create_new_alarm(self):
        return self.alarms_count < self.botSettings.ALARM_COUNT_LIMIT(self.user_type)

    # user privileges:
    @property
    def allowed_tokens_count(self):  # For now this is the same for all token selections
        return self.botSettings.TOKENS_COUNT_LIMIT(self.user_type)

    @property
    def max_alarms_count(self):
        return self.botSettings.ALARM_COUNT_LIMIT(self.user_type)

    @property
    def description(self):
        return f"{self.__str__()} - {self.firstname} - {self.premium_days_remaining}"

    @staticmethod
    def getPremiumUsers(from_date: datetime | None = None, even_possibles: bool = False):
        rows = (
            Account.database().get_premium_accounts(from_date if from_date else datetime.now())
            if not even_possibles
            else Account.database().get_possible_premium_accounts()
        )
        return [Account.extractQueryRowData(row) for row in rows]

    @staticmethod
    def database():
        if Account._database is None:
            Account._database = DatabaseInterface.get()
        return Account._database

    @staticmethod
    def extractQueryRowData(row: tuple, no_fastmem: bool = False):
        currs = row[1]
        cryptos = row[2]
        calc_currs = row[3]
        calc_cryptos = row[4]

        username = row[5]
        firstname = row[6]
        join_date = row[7]
        # add new rows here
        plus_start_date = row[-6]
        plus_end_date = row[-5]
        state = Account.States.which(row[-4])
        cache = Account.loadCache(row[-3])
        mode = int(row[-2])
        language = row[-1]
        return Account(
            chat_id=int(row[0]),
            currencies=DatabaseInterface.stringToList(currs),
            cryptos=DatabaseInterface.stringToList(cryptos),
            join_date=join_date,
            plus_end_date=plus_end_date,
            plus_start_date=plus_start_date,
            calc_currencies=DatabaseInterface.stringToList(calc_currs),
            calc_cryptos=DatabaseInterface.stringToList(calc_cryptos),
            mode=mode,
            username=username,
            firstname=firstname,
            language=language,
            state=state,
            cache=cache,
            no_fastmem=no_fastmem,
        )

    @staticmethod
    def get(chat: Chat | User, no_fastmem: bool = False):
        account = Account.getById(chat.id, no_fastmem=no_fastmem)
        account.name = chat
        return account

    @staticmethod
    def getById(chat_id: int, no_fastmem: bool = False, should_create: bool = True):
        if chat_id < 0:
            raise ValueError(
                "Account chat_id must be positive."
            )  # FIXME: Find the root of the problem: groups are creating negative ID accounts, alongside their Group model instance.
        if chat_id in Account.fastMemInstances:
            account: Account = Account.fastMemInstances[chat_id]
            account.last_interaction = tz_today()
            return account

        row = Account.database().get_account(chat_id)
        if row:
            account = Account.extractQueryRowData(row, no_fastmem=no_fastmem)
            return account

        account = Account(
            chat_id=chat_id,
            join_date=tz_today(),
            calc_cryptos=CryptoCurrencyService.getUserDefaultCryptos(),
            calc_currencies=NavasanService.getUserDefaultCurrencies(),
            no_fastmem=no_fastmem or not should_create,
        )
        if not should_create:
            return account
        return account.save()

    @staticmethod
    def getByUsername(username: str):
        if not username:
            return None
        if username[0] == "@":
            username = username[1:]
        accounts = list(filter(lambda acc: acc.username == username, list(Account.fastMemInstances.values())))
        if accounts:
            return accounts[0]

        accounts = Account.database().get_special_accounts(DatabaseInterface.ACCOUNT_USERNAME, username)
        if accounts:
            return Account.extractQueryRowData(accounts[0])
        return None

    @staticmethod
    def getHardcodeAdmin():
        return {
            "id": HARDCODE_ADMIN_CHATID,
            "username": HARDCODE_ADMIN_USERNAME,
            "account": Account.getById(HARDCODE_ADMIN_CHATID),
        }

    @staticmethod
    def loadCache(data_string: str | None):
        return json_parse(data_string) if data_string else {}

    @staticmethod
    def everybody():
        return Account.database().get_all_accounts()

    @staticmethod
    def statistics():
        # first save all last interactions:
        for kid in Account.fastMemInstances:
            Account.fastMemInstances[kid].save()
        now = tz_today().date()
        today_actives, yesterday_actives, this_week_actives, this_month_actives = 0, 0, 0, 0

        last_interactions = Account.database().get_all(column=DatabaseInterface.ACCOUNT_LAST_INTERACTION)
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
                            interaction_date.date() if isinstance(interaction_date, datetime) else interaction_date
                        )
                        if delta and delta.days == 1:
                            yesterday_actives += 1
                elif now.year == interaction_date.year + 1 and now.month == 1 and interaction_date.month == 12:
                    delta = now - (
                        interaction_date.date() if isinstance(interaction_date, datetime) else interaction_date
                    )
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
    def getAdmins(just_hardcode_admin: bool = True):
        if not just_hardcode_admin:
            admins = list(
                map(lambda data: Account.extractQueryRowData(data), Account.database().get_special_accounts())
            )
            if HARDCODE_ADMIN_CHATID:
                admins.insert(0, Account.getHardcodeAdmin()["account"])
            return admins
        return [
            Account.getHardcodeAdmin()["account"],
        ]

    def mayInteract(self):
        long_time_no_see = (
            self.no_interaction_duration() >= Account.FastMemGarbageCollectionInterval
        )  # TODO: Check out unit: Needs to convert to secs?
        if long_time_no_see:
            self.save()
            return False
        return True

    @staticmethod
    def garbageCollect():
        now = now_in_minute()
        if now - Account.PreviousFastMemGarbageCollectionTime <= Account.FastMemGarbageCollectionInterval:
            return
        Account.PreviousFastMemGarbageCollectionTime = now

        Account.fastMemInstances = {
            chat_id: account for chat_id, account in Account.fastMemInstances.items() if account.mayInteract()
        }
        gc.collect()

    @staticmethod
    def refreshFastMem():
        Account.fastMemInstances.clear()
        gc.collect()

    @staticmethod
    def getFast(chat_id: int):
        return Account.fastMemInstances[chat_id] if chat_id in Account.fastMemInstances else None

    @staticmethod
    def schedulePostsForRemoval(posts: List[Tuple[int, int, int, int]]):
        return Account.database().schedule_messages_for_removal(posts)

    @staticmethod
    def selectAccounts(take: int = 20, page: int = 0, only_premiums: bool = True):
        accounts_query_data = Account.database().select_accounts(
            limit=take, offset=take * page, only_premiums=only_premiums
        )
        return list(
            map(
                lambda row: Account.extractQueryRowData(
                    row,
                    no_fastmem=True,
                ),
                accounts_query_data,
            )
        )

    @staticmethod
    def getPremiumUsersCount():
        return Account.database().get_premium_users_count()
