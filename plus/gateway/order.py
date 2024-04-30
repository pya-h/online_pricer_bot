from plus.models.account import AccountPlus
from tools.mathematix import tz_today
from plus.models.plusplan import PlusPlan
from typing import Union
class Order:
    def wrap_required_payment_verification_data(self) -> str:
        now = tz_today()
        return f"{self.buyer.chat_id}-{self.plus_plan.id}-{now.strftime('%Y%m%d%H%M%S')}"

    def __init__(self, buyer : AccountPlus, plus_plan_id: int) -> None:
        self.plus_plan = PlusPlan.Get(plus_plan_id)
        self.buyer: AccountPlus = buyer
        self.id = self.wrap_required_payment_verification_data()
        self.cost: int = self.plus_plan.price
        self.cost_currency = self.plus_plan.price_currency
        self.description: str = f"{self.plus_plan.title}: {self.plus_plan.description}"

    @staticmethod
    def ExtractPaymentData(data: str) -> Union[int, int, str]:
        parts = data.split('-')
        return int(parts[0]), int(parts[1]), parts[2]