from enum import Enum
from tools.manuwriter import load_json
from decouple import config
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from json import dumps as jsonify
from typing import List


class ResourceManager:

    def __init__(self, source_filename: str, source_foldername: str):
        self.source = load_json(source_filename, source_foldername)

    def mainkeyboard(self, key: str, language: str = 'fa') -> str:
        return self.source['main_keyboard'][key][language]
    
    def text(self, text_key: str, language: str = 'fa') -> str:
        return self.source[text_key][language]

    def keyboard(self, key: str, language: str = 'fa') -> str:
        return self.source['keyboard'][key][language]

resourceman = ResourceManager('texts', 'resources')

class BotMan:
    '''This class is defined to collect all common and handy options, fields and features of online pricer bot'''
    class Commands(Enum):
        GET_FA = resourceman.mainkeyboard('get_prices')
        CONFIG_PRICE_LIST_FA = resourceman.mainkeyboard('config_lists')
        EQUALIZER_FA = resourceman.mainkeyboard('calculator')
        CRYPTOS_FA = resourceman.keyboard('crypto')
        NATIONAL_CURRENCIES_FA = resourceman.keyboard('currency')
        GOLDS_FA = resourceman.keyboard('gold')
        CANCEL_FA = resourceman.keyboard('return')

        ADMIN_POST_FA = 'اطلاع رسانی'
        ADMIN_START_SCHEDULE_FA = 'زمانبندی کانال'
        ADMIN_STOP_SCHEDULE_FA = 'توقف زمانبندی'
        ADMIN_STATISTICS_FA = 'آمار'

        RETURN_FA = resourceman.keyboard('return')

    def __init__(self) -> None:
        self.resourceman = resourceman
        # environment values
        self.token: str = config('BOT_TOKEN')
        self.main_channel_id: int = config('CHANNEL_ID')
        self.supporting_channel_id: int = config('SECOND_CHANNEL_ID')
        self.main_queue_id: str = config('MAIN_SCHEDULER_IDENTIFIER')

        self.text = self.resourceman.text
        
        # TODO: Update these to be dynamic with languages.
        self.menu_main_keys = [
            [KeyboardButton(BotMan.Commands.CONFIG_PRICE_LIST_FA.value), KeyboardButton(BotMan.Commands.GET_FA.value)],
            [KeyboardButton(BotMan.Commands.EQUALIZER_FA.value)],
        ]
        self.menu_main: ReplyKeyboardMarkup = ReplyKeyboardMarkup(self.menu_main_keys, resize_keyboard=True)

        self.admin_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup([*self.menu_main_keys,
            [KeyboardButton(BotMan.Commands.ADMIN_POST_FA.value), KeyboardButton(BotMan.Commands.ADMIN_STATISTICS_FA.value)],
            [KeyboardButton(BotMan.Commands.ADMIN_START_SCHEDULE_FA.value), KeyboardButton(BotMan.Commands.ADMIN_STOP_SCHEDULE_FA.value)],
        ], resize_keyboard=True)

        self.cancel_menu_key = [
            [KeyboardButton(BotMan.Commands.CANCEL_FA.value)],
        ]

        self.return_key = [
            [KeyboardButton(BotMan.Commands.RETURN_FA.value)],
        ]

        self.bazaars_menu_keys = ReplyKeyboardMarkup([
            [KeyboardButton(BotMan.Commands.NATIONAL_CURRENCIES_FA.value)], [KeyboardButton(BotMan.Commands.GOLDS_FA.value)],
            [KeyboardButton(BotMan.Commands.CRYPTOS_FA.value)], *self.return_key
        ], resize_keyboard=True)

    def mainkeyboard(self, is_admin: bool) -> ReplyKeyboardMarkup:
        return self.menu_main if not is_admin else self.admin_keyboard


    @staticmethod
    def inline_keyboard(name, all_choices: dict, selected_ones: list=None, show_full_names: bool=False):
        '''this function creates inline keyboard for selecting/deselcting some options'''
        if not selected_ones:
            selected_ones = []
        buttons = []
        row = []
        i = 0
        for choice in all_choices:
            btn_text = choice if not show_full_names else all_choices[choice]
            i += 1 + int(len(btn_text) / 5)
            if choice in selected_ones:
                btn_text += "✅"
            row.append(InlineKeyboardButton(btn_text, callback_data=jsonify({"type": name, "value": choice})))
            if i >= 5:
                buttons.append(row)
                row = []
                i = 0
        # buttons.append([InlineKeyboardButton("ثبت!", callback_data=jsonify({"type": name, "value": "#OK"}))])
        return InlineKeyboardMarkup(buttons)
    
    def keyboard_from(self, language: str, *row_keys: List[str]):
        btns = []
        for key in row_keys:
            btns.append([self.resourceman.keyboard(key, language)])
        return ReplyKeyboardMarkup(btns, resize_keyboard=True)


