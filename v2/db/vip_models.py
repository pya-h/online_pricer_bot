from db.account import Account, UserStates
from tools.mathematix import tz_today
from db.vip_interface import VIPDatabaseInterface
from datetime import datetime


class VIPAccount(Account):

    MaxSelectionInDesiredOnes = 100
    Database = VIPDatabaseInterface.Get()

    def __init__(self, chat_id: int, currencies: list=None, cryptos: list=None, language: str = 'fa', vip_end_date: datetime = None) -> None:
        super().__init__(chat_id, currencies, cryptos, language)
        self.vip_end_date = vip_end_date

    @staticmethod
    def Get(chat_id):
        if chat_id in VIPAccount.Instances:
            VIPAccount.Instances[chat_id].last_interaction = tz_today()
            return VIPAccount.Instances[chat_id]
        row = VIPAccount.Database.get(chat_id)
        if row:
            currs = row[1] if not row[1] or row[1][-1] != ";" else row[1][:-1]
            cryptos = row[2] if not row[2] or row[2][-1] != ";" else row[2][:-1]
            vip_end_date = datetime.strptime(row[-1], VIPDatabaseInterface.DATE_FORMAT) if row[-1] else None
            return VIPAccount(chat_id=int(row[0]), currencies=currs.split(";") if currs else None, cryptos=cryptos.split(';') if cryptos else None, vip_end_date=vip_end_date)

        return VIPAccount(chat_id=chat_id).save()



class Channel:
    Instances = {}
    Database: VIPDatabaseInterface = VIPDatabaseInterface.Get()

    def __init__(self, owner_id: int, channel_id: int, channel_name: str, interval: int = 0) -> None:
        self.owner_id = owner_id
        self.id = channel_id
        self.name = channel_name
        self.interval = interval
        if interval > 0:
            self.plan(interval)

    def plan(self, interval: int):
        if interval <= 0:
            if self.id in Channel.Instances:
                del Channel.Instances[self.id]
                # unplan in database
            return

        if interval < 60:
            Channel.Instances[self.id] = self
        Channel.Database.plan_channel(self.owner_id, self.id, self.name, interval)

    @staticmethod
    def Get(channel_id):
        if channel_id in Channel.Instances:
            return Channel.Instances[channel_id]
        row = Channel.Database.get_channel(channel_id)
        if row:
            return Channel(channel_id=int(row[0]), owner_id=int(row[3]), channel_name=row[1], interval=int(row[2]))

        return None
