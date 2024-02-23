from db.vip_models import VIPAccount
from tools.mathematix import tz_today

class Order:
    DiscountPercent = 0.2
    DiscountStartMonth = 12
    CostPerMonth = 5
    CostUnit = "USDT"

    def __init__(self, buyer : VIPAccount, months_counts:int = 2) -> None:
        self.months_counts: int = months_counts
        self.buyer: VIPAccount = buyer
        now = tz_today()
        self.order_id: str = f"{buyer.chat_id}-{now.strftime("%Y%m%d%H%M%S")}"
        self.cost: int = self.months_counts * Order.CostPerMonth
        if months_counts >= Order.DiscountStartMonth:
            self.cost -= self.cost * 0.2
        self.description: str = f"VIP Account Payment For {self.months_counts} Months"
