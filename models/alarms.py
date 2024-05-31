from enum import Enum
from typing import List
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

        @staticmethod
        def Which(direction_value: int):
            match direction_value:
                case PriceAlarm.ChangeDirection.EXACT.value: 
                    return PriceAlarm.ChangeDirection.EXACT
                case PriceAlarm.ChangeDirection.DOWN.value:
                    return PriceAlarm.ChangeDirection.DOWN
            return PriceAlarm.ChangeDirection.UP

    def __init__(self, chat_id, currency_symbol: str, target_price: int | float, change_direction: ChangeDirection | int, target_unit: str = 'IRT', id: int = 0) -> None:
        self.id = id
        self.chat_id = chat_id
        self.currency_symbol = currency_symbol
        self.target_price = target_price
        self.target_unit = target_unit
        self.change_direction = change_direction if isinstance(change_direction, PriceAlarm.ChangeDirection) else PriceAlarm.ChangeDirection.Which(change_direction)

    @staticmethod
    def Get(currencies: List[str] | None = None):
        rows = PriceAlarm.Database().get_alarms_by_currencies(currencies) if currencies else PriceAlarm.Database().get_alarms()
        
        if channel_id in Channel.Instances:
            return Channel.Instances[channel_id]
        row = Channel.Database.get_channel(channel_id)
        if row:
            return Channel(channel_id=int(row[0]), interval=int(row[1]), last_post_time=int(row[2]), channel_name=row[3], channel_title=row[4], owner_id=int(row[-1]))

        return None
