from enum import Enum
from typing import List, Dict
from db.interface import DatabaseInterface

class PriceAlarm:
    _database: DatabaseInterface = None

    @staticmethod
    def Database():
        if PriceAlarm._database is None:
            PriceAlarm._database = DatabaseInterface.Get()
        return PriceAlarm._database

    class ChangeDirection(Enum):
        EXACT = 0
        UP = 1
        DOWN = 2

        def __str__(self) -> str:
            match self.value:
                case PriceAlarm.ChangeDirection.EXACT:
                    return 'is exactly'
                case PriceAlarm.ChangeDirection.UP:
                    return 'is above'
            return 'is below'

        @staticmethod
        def Which(direction_value: int):
            match direction_value:
                case PriceAlarm.ChangeDirection.EXACT.value:
                    return PriceAlarm.ChangeDirection.EXACT
                case PriceAlarm.ChangeDirection.DOWN.value:
                    return PriceAlarm.ChangeDirection.DOWN
            return PriceAlarm.ChangeDirection.UP

    def __init__(self, chat_id, currency: str, target_price: int | float, change_direction: ChangeDirection | int | None = None, target_unit: str = 'irt', id: int = None, current_price: float | int | None = None) -> None:
        self.id = id
        self.chat_id = chat_id
        self.currency = currency
        self.target_price = target_price
        self.target_unit = target_unit
        if change_direction is None and current_price is not None:
            if current_price < target_price:
                self.change_direction = PriceAlarm.ChangeDirection.UP
            else:
                self.change_direction = PriceAlarm.ChangeDirection.DOWN
        else:
            self.change_direction = change_direction if isinstance(change_direction, PriceAlarm.ChangeDirection) else PriceAlarm.ChangeDirection.Which(change_direction)
        self.current_price: int | None = None
        self.full_currency_name: Dict[str, str] | None = None

    def ExtractQueryRowData(row: tuple):
        return PriceAlarm(row[1], row[3], row[2], row[4], row[5], row[0])
    
    def GetByUser(self, chat_id: int):
        rows = self.Database().get_user_alarms(chat_id)
        return list(map(PriceAlarm.ExtractQueryRowData, rows))
        
    @staticmethod
    def Get(currencies: List[str] | None = None):
        rows = PriceAlarm.Database().get_alarms_by_currencies(currencies) if currencies else PriceAlarm.Database().get_alarms()
        return list(map(PriceAlarm.ExtractQueryRowData, rows))

    def disable(self):
        self.Database().delete_alarm(self.id)

    def set(self):
        db = self.Database()
        if self.id:
            rows = db.get_single_alarm(self.id)
            if rows and len(rows):
                return
        self.id = db.create_new_alarm(self)

    def __str__(self) -> str:
        return f'Alarm for when {self.currency} {self.change_direction} {self.target_price} {self.target_unit}'
