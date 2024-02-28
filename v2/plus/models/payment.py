from tools.mathematix import now_in_minute
from plus.models.plusplan import PlusPlan
import json
from plus.db.interface import DatabasePlusInterface


class Payment:
    OngoingPayments = {}
    PaymentDumpInterval = 60 # in minutes
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
        Payment.GarbageCollect()  # or add a timer?
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