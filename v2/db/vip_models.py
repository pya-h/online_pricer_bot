from db.account import Account
from tools.mathematix import tz_today
from db.vip_interface import VIPDatabaseInterface
from datetime import datetime
from tools.exceptions import NotVIPException
from enum import Enum
import json
from payagraph.raw_materials import CanBeKeyboardItemInterface


class PlanInterval(CanBeKeyboardItemInterface):
    def __init__(self, title: str, minutes: int = 0, hours: int = 0, days: int = 0) -> None:
        self._title = title
        self.days = days
        self.hours = hours + self.days * 24  # total in hours
        self.mins = minutes + self.hours * 60  # total interval in minutes

    def value(self) -> int:
        return self.mins  # this is for InlineKeyboared.Arrange

    def title(self) -> str:
        return self._title

    def as_json(self):
        return json.dumps({"d": self.days, "h": self.hours, "m": self.mins})


class Channel:

    Instances = {}
    Database: VIPDatabaseInterface = VIPDatabaseInterface.Get()

    @staticmethod
    def GetHasPlanChannels():
        '''return all channel table rows that has interval > 0'''
        # TODO: load from databbase
        return Channel.Instances
    
    SupportedIntervals: list[PlanInterval] = [
        PlanInterval("1 MIN", minutes=1), *[PlanInterval(f"{m} MINS", minutes=m) for m in [2, 5, 10, 30, 45]],
        PlanInterval("1 HOUR", hours=1), *[PlanInterval(f"{h} HOURS", hours=h) for h in [2, 3, 4, 6, 12]],
        PlanInterval("1 DAY", days=1), *[PlanInterval(f"{d} DAYS", days=d) for d in [2, 3, 4, 5, 6, 7, 10, 14, 30, 60]]
    ]

    def __init__(self, owner_id: int, channel_id: int, channel_name: str, interval: int = 0) -> None:
        self.owner_id = owner_id
        self.id = channel_id
        self.name = channel_name
        self.interval = interval
        
    def plan(self) -> bool:
        if self.interval <= 0:
            if self.id in Channel.Instances:
                # unplan and delete in database
                del Channel.Instances[self.id]
            return False  # Plan removed

        # if self.interval < 60:
        #     Channel.Instances[self.id] = self
        Channel.Instances[self.id] = self
        Channel.Database.plan_channel(self.owner_id, self.id, self.name, self.interval)
        return True


    @staticmethod
    def Get(channel_id):
        if channel_id in Channel.Instances:
            return Channel.Instances[channel_id]
        row = Channel.Database.get_channel(channel_id)
        if row:
            return Channel(channel_id=int(row[0]), owner_id=int(row[3]), channel_name=row[1], interval=int(row[2]))

        return None


class UserStates(Enum):
    NONE = 0
    SELECT_CHANNEL = 4
    SELECT_INTERVAL = 5
class VIPAccount(Account):

    MaxSelectionInDesiredOnes = 100
    _database = None

    @staticmethod
    def Database():
        if VIPAccount._database == None:
            VIPAccount._database = VIPDatabaseInterface.Get()
        return VIPAccount._database

    def __init__(self, chat_id: int, currencies: list=None, cryptos: list=None, language: str = 'fa', vip_end_date: datetime = None) -> None:
        super().__init__(chat_id, currencies, cryptos, "en")#language)
        self.state: UserStates = UserStates.NONE
        self.vip_end_date = vip_end_date

    @staticmethod
    def Get(chat_id):
        if chat_id in VIPAccount.Instances:
            VIPAccount.Instances[chat_id].last_interaction = tz_today()
            return VIPAccount.Instances[chat_id]
        row = VIPAccount.Database().get(chat_id)
        if row:
            currs = row[1] if not row[1] or row[1][-1] != ";" else row[1][:-1]
            cryptos = row[2] if not row[2] or row[2][-1] != ";" else row[2][:-1]
            vip_end_date = datetime.strptime(row[-1], VIPDatabaseInterface.DATE_FORMAT) if row[-1] else None
            return VIPAccount(chat_id=int(row[0]), currencies=currs.split(";") if currs else None, cryptos=cryptos.split(';') if cryptos else None, vip_end_date=vip_end_date)

        return VIPAccount(chat_id=chat_id).save()

    def has_vip_privileges(self) -> bool:
        '''Check if the account has still vip subscription.'''
        return True   # TODO: DELETE THIS *****
        return self.vip_end_date is not None and tz_today().date() <= self.vip_end_date.date()

    def plan_new_channel(self, channel_id: int, channel_name: str, interval: int) -> Channel:
        if not self.has_vip_privileges():
            raise NotVIPException(self.chat_id)
        channel = Channel(self.chat_id, channel_id, channel_name, interval)  
        if channel.plan():
            return channel
        return None

    @staticmethod
    def Everybody():
        return VIPAccount.Database().get_all()

    @staticmethod
    def GarbageCollect():
        now = tz_today()
        garbage = []
        for chat_id in VIPAccount.Instances:
            if (now - VIPAccount.Instances[chat_id].last_interaction).total_seconds() / 60 >= VIPAccount.GarbageCollectionInterval / 2:
                garbage.append(chat_id)
        # because changing dict size in a loop on itself causes error,
        # we first collect redundant chat_id s and then delete them from the memory
        for g in garbage:
            del VIPAccount.Instances[g]
