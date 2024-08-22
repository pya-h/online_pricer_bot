from enum import Enum


class MarketOptions(Enum):
    CRYPTO = 1
    CURRENCY = 2
    GOLD = 3

    @staticmethod
    def which(value: int):
        for option in (
            MarketOptions.CRYPTO,
            MarketOptions.CURRENCY,
            MarketOptions.GOLD,
        ):
            if option.value == value:
                return option
        return None
class SelectionListTypes(Enum):
    USER_TOKENS = 1
    CALCULATOR = 2
    CHANNEL = 3
    NOTIFICATION = 4
    EQUALIZER_UNIT = 5
    ALARM = 6
    GROUP_TOKENS = 7
    CHANNEL_TOKENS = 8

    @staticmethod
    def which(value: int):
        for option in (
            SelectionListTypes.USER_TOKENS,
            SelectionListTypes.CALCULATOR,
            SelectionListTypes.CHANNEL,
            SelectionListTypes.NOTIFICATION,
            SelectionListTypes.EQUALIZER_UNIT,
            SelectionListTypes.ALARM,
        ):
            if option.value == value:
                return option
        return None


class GroupInlineKeyboardButtonTemplate:
    @property
    def value(self) -> int:
        pass

    @property
    def title(self) -> str:
        pass
