from plus.db.interface import DatabasePlusInterface
from payagraph.raw import CanBeKeyboardItemInterface
import json


class PlusPlan:

    def __init__(self, title: str, description: str, duration_in_months: int, plus_level: int, price: float, price_currency: str, id: int=None, title_en: str = None, description_en: str = None) -> None:
        self.id: int = id
        self.title: str = title
        self.description: str = description
        self.duration_in_months: int = duration_in_months
        self.plus_level: int = plus_level
        self.price: float = price
        self.price_currency: str = price_currency
        self.title_en = title_en
        self.description_en = description_en

    @staticmethod
    def Get(id: int):
        row = DatabasePlusInterface.Get().get_plus_plan(id)
        return PlusPlan.ExtractRow(row)

    @staticmethod
    def ExtractRow(row: list):
        return PlusPlan(id=row[0], price=row[1], price_currency=row[2], duration_in_months=row[3], plus_level=row[4], title=row[5], title_en=row[6], description=row[7], description_en=row[8])

    @staticmethod
    def PlusPlansList():
        plans: list[PlusPlan] = DatabasePlusInterface.Get().get_all_plus_plans()
        return list(map(PlusPlan.ExtractRow, plans))

    @staticmethod
    def Define(title: str, title_en: str, duration_in_months: int, price: float, price_currency: str = "USDT", plus_level: int = 1) -> bool:
        try:
            DatabasePlusInterface().Get().define_plus_plan(title=title, titile_en=title_en, duration_in_months=duration_in_months, price=price, price_currency=price_currency, plus_level=plus_level)
        except:
            return False

        return True

    def save(self):
        DatabasePlusInterface.Get().update_plus_plan(self)
        return self


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
