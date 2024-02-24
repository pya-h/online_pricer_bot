from db.account import Account
from tools.mathematix import tz_today
from db.interface_plus import DatabasePlusInterface
from datetime import datetime
from tools.exceptions import NotPlusException
from enum import Enum
import json
from payagraph.raw_materials import CanBeKeyboardItemInterface
from tools import manuwriter
from tools.mathematix import now_in_minute

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



class PlusPlan:
    
    def __init__(self, title: str, description: str, duration_in_months: int, plus_level: int, price: float, price_currency: str, id: int=None) -> None:
        self.id: int = id
        self.title: str = title
        self.description: str = description
        self.duration_in_months: int = duration_in_months
        self.plus_level: int = plus_level
        self.price: float = price
        self.price_currency: str = price_currency
        
    @staticmethod
    def Get(id: int):
        row = DatabasePlusInterface.Get().get_plus_plan(id)
        return PlusPlan.ExtractRow(row)
    
    @staticmethod
    def ExtractRow(row: list):
        return PlusPlan(id=row[0], title=row[1], description=row[2], duration_in_months=row[3], plus_level=row[4], price=row[5], price_currency=row[6])

    @staticmethod
    def PlusPlansList():
        plans: list[PlusPlan] = DatabasePlusInterface.Get().get_plus_plan()
        return list(map(PlusPlan.ExtractRow, plans))
       
    @staticmethod
    def Define(title: str, description: str, duration_in_months: int, price: float, price_currency: str = "USDT", plus_level: int = 1) -> bool:
        try:
            DatabasePlusInterface().Get().define_plus_plan(title, description, duration_in_months, price, price_currency, plus_level) 
        except:
            return False
        
        return True

    def save(self):
        DatabasePlusInterface.Get().update_plus_plan(self)
        return self
    
        
class Channel:

    Instances = {}
    Database: DatabasePlusInterface = DatabasePlusInterface.Get()

    @staticmethod
    def GetHasPlanChannels():
        '''return all channel table rows that has interval > 0'''
        Channel.Instances.clear()
        channels_as_row = Channel.Database.get_channels_by_interval()  # fetch all positive interval channels
        for row in channels_as_row:
            channel = Channel(channel_id=int(row[0]), interval=int(row[1]), last_post_time=int(row[2]), channel_name=row[3], channel_title=row[4], owner_id=int(row[-1]))
            Channel.Instances[channel.id] = channel
        return Channel.Instances

    SupportedIntervals: list[PlanInterval] = [
        PlanInterval("1 MIN", minutes=1), *[PlanInterval(f"{m} MINS", minutes=m) for m in [2, 5, 10, 30, 45]],
        PlanInterval("1 HOUR", hours=1), *[PlanInterval(f"{h} HOURS", hours=h) for h in [2, 3, 4, 6, 12]],
        PlanInterval("1 DAY", days=1), *[PlanInterval(f"{d} DAYS", days=d) for d in [2, 3, 4, 5, 6, 7, 10, 14, 30, 60]]
    ]

    def __init__(self, owner_id: int, channel_id: int, interval: int = 0, channel_name: str = None, channel_title:str = None, last_post_time: int=None) -> None:
        self.owner_id = owner_id
        self.id = channel_id
        self.name = channel_name  # username
        self.title = channel_title
        self.interval = interval
        self.last_post_time = last_post_time  # dont forget database has this

    def plan(self) -> bool:
        if self.interval <= 0:
            if self.id in Channel.Instances:
                # unplan and delete in database
                del Channel.Instances[self.id]
            return False  # Plan removed

        # if self.interval < 60:
        #     Channel.Instances[self.id] = self
        Channel.Instances[self.id] = self
        Channel.Database.plan_channel(self.owner_id, self.id, self.name, self.interval, self.title)
        return True

    def stop_plan(self) -> bool:
        try:
            Channel.Database.delete_channel(self.id)
            del Channel.Instances[self.id]
        except Exception as ex:
            manuwriter.log(f'Cannot remove chnnel:{self.id}', ex, category_name="PLUS_FATALITY")
            return False
        return True

    @staticmethod
    def Get(channel_id):
        if channel_id in Channel.Instances:
            return Channel.Instances[channel_id]
        row = Channel.Database.get_channel(channel_id)
        if row:
            return Channel(channel_id=int(row[0]), interval=int(row[1]), last_post_time=int(row[2]), channel_name=row[3], channel_title=row[4], owner_id=int(row[-1]))

        return None

    def __str__(self) -> str:
        return f"Username:{self.name}\nTitle: {self.title}\nId: {self.id}\nInterval: {self.interval}\nOwner Id: {self.owner_id}"

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

    def has_plus_privileges(self) -> bool:
        '''Check if the account has still plus subscription.'''
        return self.plus_end_date is not None and tz_today().date() <= self.plus_end_date.date() and self.plus_plan_id

    def plan_new_channel(self, channel_id: int, interval: int, channel_name: str, channel_title: str = None) -> Channel:
        if not self.has_plus_privileges():
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
        
class Payment:
    OngoingPayments = {}
    PaymentDumpInterval = 100 # in minutes
    PreviousDumpTime: int = now_in_minute()
    
    def load_query_row(self, query_row: list):
        '''Literal['order_id'], Literal['chat_id'], Literal['id'], Literal['status'],
        Literal['amount'], Literal['currency'], Literal['paid_amount'], Literal['paid_currency'],
        Literal['plus_plan_id'], Literal['created'], Literal['modified']'''
        self.order_id = str(query_row[0])
        self.shortdate = [int(part) for part in self.order_id.split('_')][-1]
        self.payer_chat_id = int(query_row[1])
        self.id = int(query_row[2])
        self.status = query_row[3].lower()
        self.amount = float(query_row[4])
        self.currency = query_row[5].upper()
        self.paid_amount = float(query_row[6]) 
        self.paid_currency = query_row[7]
        plus_plan_id = int(query_row[8])
        self.plus_plan = PlusPlan.Get(plus_plan_id)
        self.created_at = query_row[9]
        self.modified_at = query_row[10]
    
    def load_nowpayment_data(self, data: dict|str):
        if isinstance(data, str):
            data = json.loads(data)
        self.order_id = str(data["order_id"])
        plan_id, self.payer_chat_id, self.shortdate = [int(part) for part in self.order_id.split('_')]
        self.plus_plan = PlusPlan.Get(plan_id)
        self.id = int(data["payment_id"])
        self.status = data["payment_status"].lower()
        self.amount = float(data["price_amount"])
        self.currency = data["price_currency"].upper()
        self.paid_amount = float(data["pay_amount"]) 
        self.paid_currency = data["pay_currency"].upper()
        self.created_at = data["created_at"]
        self.modified_at = data["updated_at"]  
          
    def update_ongoings(self):
        Payment.GarbageCollect()
        Payment.OngoingPayments[self.order_id] = self
      
    @staticmethod
    def GarbageCollect():
        # first remove expired payments
        now = now_in_minute()
        if now - Payment.PreviousDumpTime < Payment.PaymentDumpInterval / 5:
            return
        Payment.PreviousDumpTime = now
        garbage = []
        for order_id in Payment.OngoingPayments:
            payment: Payment = Payment.OngoingPayments[order_id]
            if (now - payment.instance_birth_time) >= Payment.PaymentDumpTime:
                garbage.append(order_id)

        for g in garbage:
            del Payment.OngoingPayments[g]
        
    def __init__(self, data) -> None:
        self.instance_birth_time = now_in_minute()
        self.order_id: str = ''
        self.shortdate: int = None
        self.payer_chat_id: int = None
        self.id: int = None
        self.status: str = ''
        self.amount: float = None
        self.currency: str = ''
        self.paid_amount: int = None 
        self.paid_currency: str = ''
        self.plus_plan: PlusPlan = None
        self.created_at: str = ''
        self.modified_at: str = ''
        
        if isinstance(data, dict):
            self.load_nowpayment_data(data)
            self.update_ongoings()
        elif isinstance(data, list):
            self.load_query_row(data)
            self.update_ongoings()
          
    @staticmethod
    def Get(order_id):
        try:
            return Payment.OngoingPayments[order_id]
        except:
            pass
        return Payment(DatabasePlusInterface.Get().get_payment(order_id))
    
    def save(self):
        DatabasePlusInterface.Get().update_payment(self)
        return self