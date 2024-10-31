from enum import Enum
from tools.manuwriter import load_json


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
            SelectionListTypes.GROUP_TOKENS,
            SelectionListTypes.CHANNEL_TOKENS,
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


class ResourceManager:

    def __init__(self, source_filename: str, source_foldername: str):
        self.source = load_json(source_filename, source_foldername)

    def mainkeyboard(self, key: str, language: str = "fa") -> str:
        return self.source["main_keyboard"][key][language.lower()]

    def text(self, text_key: str, language: str = "fa") -> str:
        return self.source[text_key][language.lower()]

    def text_for_case_sensitive_key(self, text_key: str, language: str = "fa") -> str: # this is just for preventing the main func (text(...) always check a condition which only be True for 1 or 2 times in whole app)
        return self.source[text_key][language]

    def get(self, text_key: str):
        return self.source[text_key]

    def error(self, text_key: str, language: str = "fa") -> str:
        return self.source["errors"][text_key][language.lower()]

    def keyboard(self, key: str, language: str = "fa") -> str:
        return self.source["keyboard"][key][language.lower()]