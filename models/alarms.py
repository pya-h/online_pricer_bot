from enum import Enum
from typing import List, Dict
from db.interface import DatabaseInterface
from .account import Account


class PriceAlarm:
    _database: DatabaseInterface = None

    @staticmethod
    def database():
        if PriceAlarm._database is None:
            PriceAlarm._database = DatabaseInterface.get()
        return PriceAlarm._database

    class ChangeDirection(Enum):
        EXACT = 0
        UP = 1
        DOWN = 2

        def __str__(self) -> str:
            match self.value:
                case PriceAlarm.ChangeDirection.EXACT:
                    return "is exactly"
                case PriceAlarm.ChangeDirection.UP:
                    return "is above"
            return "is below"

        @staticmethod
        def which(direction_value: int):
            match direction_value:
                case PriceAlarm.ChangeDirection.EXACT.value:
                    return PriceAlarm.ChangeDirection.EXACT
                case PriceAlarm.ChangeDirection.DOWN.value:
                    return PriceAlarm.ChangeDirection.DOWN
            return PriceAlarm.ChangeDirection.UP

    def __init__(
        self,
        chat_id: int,
        currency: str,
        target_price: int | float,
        change_direction: ChangeDirection | int | None = None,
        target_unit: str = "irt",
        id: int = None,
        current_price: float | int | None = None,
    ) -> None:
        self.id = id
        self.chat_id = int(chat_id)
        self.owner: Account | None = None
        self.currency = currency
        self.target_price = target_price
        self.target_unit = target_unit
        if change_direction is None and current_price is not None:
            if current_price < target_price:
                self.change_direction = PriceAlarm.ChangeDirection.UP
            else:
                self.change_direction = PriceAlarm.ChangeDirection.DOWN
        else:
            self.change_direction = (
                change_direction
                if isinstance(change_direction, PriceAlarm.ChangeDirection)
                else PriceAlarm.ChangeDirection.which(change_direction)
            )
        self.current_price: int | None = None
        self.full_currency_name: Dict[str, str] | None = None

    def extractQueryRowData(row: tuple):
        return PriceAlarm(row[1], row[3], row[2], row[4], row[5], row[0])

    @staticmethod
    def getAlarms(id: int):
        # FIXME: This must get all alarms
        return PriceAlarm.getUserAlarms(id)

    @staticmethod
    def getUserAlarms(chat_id: int):
        rows = PriceAlarm.database().get_user_alarms(int(chat_id))
        return list(map(PriceAlarm.extractQueryRowData, rows))

    @staticmethod
    def get(currencies: List[str] | None = None):
        # FIXME: Use SQL 'JOIN ON' keyword to load group and owner accounts simultaneously.
        rows = PriceAlarm.database().get_alarms_by_currencies(currencies) if currencies else PriceAlarm.database().get_alarms()
        return list(map(PriceAlarm.extractQueryRowData, rows))

    def disable(self):
        self.database().delete_alarm(self.id)

    @staticmethod
    def disableById(alarm_id):
        """Efficient way to disable alarms when there is just an id available"""
        PriceAlarm.database().delete_alarm(alarm_id)

    def set(self):
        db = self.database()
        if self.id:
            rows = db.get_single_alarm(self.id)
            if rows and len(rows):
                return
        self.id = db.create_new_alarm(self)

    def __str__(self) -> str:
        return f"Alarm for when {self.currency} {self.change_direction} {self.target_price} {self.target_unit}"
