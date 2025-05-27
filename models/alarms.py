from enum import Enum
from typing import List, Dict
from typing_extensions import Self
from db.interface import DatabaseInterface
from .account import Account
from tools.exceptions import InvalidInputException
from bot.types import MarketOptions


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
        token: str,
        target_price: int | float,
        change_direction: ChangeDirection | int | None = None,
        target_unit: str = "irt",
        market: MarketOptions = MarketOptions.CRYPTO,
        id: int = None,
        current_price: float | int | None = None,
    ) -> None:
        self.id = id
        self.chat_id = int(chat_id)
        self.token = token
        self.target_price: float | int = target_price
        self.target_unit: str = target_unit
        self.market: MarketOptions = market
        self.current_price: int | None = current_price
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
            if self.current_price and not self.is_reasonable:
                raise InvalidInputException(
                    "specified change direction and target price doesn't match with token's current price."
                )
        self.full_token_name: Dict[str, str] | None = None
        self.owner: Account | None = Account.getFast(
            self.chat_id
        )  # TODO: Use SQL JOIN and Use it In case fastmem is empty

    def set(self):
        db = self.database()
        if self.id:
            rows = db.get_single_alarm(self.id)
            if rows and len(rows):
                return
        self.id = db.create_new_alarm(self)

    def __str__(self) -> str:
        return f"Alarm for when {self.token} {self.change_direction} {self.target_price} {self.target_unit}"

    @property
    def is_reasonable(self):
        return (
            (self.change_direction == PriceAlarm.ChangeDirection.UP and self.current_price < self.target_price)
            or (self.change_direction == PriceAlarm.ChangeDirection.DOWN and self.current_price > self.target_price)
            or (self.change_direction == PriceAlarm.ChangeDirection.EXACT and self.current_price != self.target_price)
        )

    @staticmethod
    def extractQueryRowData(row: tuple):
        return PriceAlarm(
            id=row[0],
            chat_id=row[1],
            token=row[2],
            target_price=row[3],
            market=MarketOptions.which(row[4]),
            change_direction=row[5],
            target_unit=row[6],
        )

    @staticmethod
    def getAlarm(id: int):
        alarm_rows = PriceAlarm.database().get_single_alarm(id)
        return PriceAlarm.extractQueryRowData(alarm_rows)

    @staticmethod
    def getUserAlarms(chat_id: int):
        rows = PriceAlarm.database().get_user_alarms(chat_id)
        return list(map(PriceAlarm.extractQueryRowData, rows))

    @staticmethod
    def get(tokens: List[str] | None = None):
        # FIXME: Use SQL 'JOIN ON' keyword to load group and owner accounts simultaneously.
        rows = PriceAlarm.database().get_alarms_by_tokens(tokens) if tokens else PriceAlarm.database().get_alarms()
        return list(map(PriceAlarm.extractQueryRowData, rows))

    def disable(self):
        self.database().delete_alarm(self.id)

    @staticmethod
    def batchDisable(alarms: List[Self]):
        PriceAlarm.database().batch_delete_alarms([alarm.id for alarm in alarms])

    @staticmethod
    def disableById(alarm_id):
        """Efficient way to disable alarms when there is just an id available"""
        PriceAlarm.database().delete_alarm(alarm_id)

    @property
    def change_icon(self) -> str:
        return "🔴" if self.change_direction == PriceAlarm.ChangeDirection.DOWN else "🟢"
