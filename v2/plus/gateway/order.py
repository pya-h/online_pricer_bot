from plus.models.account import AccountPlus
from tools.mathematix import tz_today
from plus.models.plusplan import PlusPlan

class Order:

    def __init__(self, buyer : AccountPlus, plus_plan_id: int) -> None:
        self.plus_plan = PlusPlan.Get(plus_plan_id)
        self.buyer: AccountPlus = buyer
        now = tz_today()
        self.id: str = f"{buyer.chat_id}-{self.plus_plan.id}-{now.strftime('%Y%m%d%H%M%S')}"
        self.cost: int = self.plus_plan.price
        self.cost_currency = self.plus_plan.price_currency
        self.description: str = f"{self.plus_plan.title}: {self.plus_plan.description}"
