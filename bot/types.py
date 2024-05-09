from enum import Enum


class MarketOptions(Enum):
    CRYPTO = 1
    CURRENCY = 2
    GOLD = 3

    @staticmethod
    def Which(value: int):
        for option in (MarketOptions.CRYPTO, MarketOptions.CURRENCY, MarketOptions.GOLD,):
            if option.value == value:
                return option
        return None


class SelectionListTypes(Enum):
    FOLLOWING = 1
    CALCULATOR = 2
    CHANNEL = 3
    NOTIFICATION = 4
    EQUALIZER_UNIT = 5

    @staticmethod
    def Which(value: int):
        for option in (SelectionListTypes.FOLLOWING, SelectionListTypes.CALCULATOR, SelectionListTypes.CHANNEL,
                       SelectionListTypes.NOTIFICATION, SelectionListTypes.EQUALIZER_UNIT):
            if option.value == value:
                return option
        return None
