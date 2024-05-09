from enum import Enum
from tools.manuwriter import load_json
from decouple import config
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, Update
from telegram.ext import CallbackContext
from api.currency_service import CurrencyService
from api.crypto_service import CryptoCurrencyService
from json import dumps as jsonify
from typing import List
from bot.post import PostMan


class ResourceManager:

    def __init__(self, source_filename: str, source_foldername: str):
        self.source = load_json(source_filename, source_foldername)

    def mainkeyboard(self, key: str, language: str = 'fa') -> str:
        return self.source['main_keyboard'][key][language]

    def text(self, text_key: str, language: str = 'fa') -> str:
        return self.source[text_key][language]

    def error(self, text_key: str, language: str = 'fa') -> str:
        return self.source['errors'][text_key][language]

    def keyboard(self, key: str, language: str = 'fa') -> str:
        return self.source['keyboard'][key][language]


resourceman = ResourceManager('texts', 'resources')


class BotMan:
    """This class is defined to collect all common and handy options, fields and features of online pricer bot"""

    class Commands(Enum):
        GET_FA = resourceman.mainkeyboard('get_prices')
        CONFIG_PRICE_LIST_FA = resourceman.mainkeyboard('config_lists')
        CALCULATOR_FA = resourceman.mainkeyboard('calculator')
        CRYPTOS_FA = resourceman.keyboard('crypto')
        NATIONAL_CURRENCIES_FA = resourceman.keyboard('currency')
        GOLDS_FA = resourceman.keyboard('gold')
        CANCEL_FA = resourceman.keyboard('return')
        CONFIG_CALCULATOR_FA = resourceman.mainkeyboard('config_calculator')

        ADMIN_POST_FA = 'اطلاع رسانی'
        ADMIN_START_SCHEDULE_FA = 'زمانبندی کانال'
        ADMIN_STOP_SCHEDULE_FA = 'توقف زمانبندی'
        ADMIN_STATISTICS_FA = 'آمار'

        RETURN_FA = resourceman.keyboard('return')

    def __init__(self) -> None:
        self.resourceman = resourceman
        # environment values
        self.token: str = config('BOT_TOKEN')
        username: str = config('BOT_USERNAME')
        self.username = f"@{username}"
        self.url = f"https://t.me/{username}"

        CMC_API_KEY = config('COINMARKETCAP_API_KEY')
        CURRENCY_TOKEN = config('CURRENCY_TOKEN')
        ABAN_TETHER_TOKEN = config('ABAN_TETHER_TOKEN')

        self.postman = PostMan(CURRENCY_TOKEN, ABAN_TETHER_TOKEN, CMC_API_KEY)

        self.channels = [
            {'id': config('CHANNEL_ID'), 'url': config('CHANNEL_URL')},
            {'id': config('SECOND_CHANNEL_ID', None), 'url': config('SECOND_CHANNEL_URL', None)}
        ]

        self.channels[0]['username'] = config('CHANNEL_USERNAME', self.channels[0]['url'])
        if not self.channels[1]['id']:
            del self.channels[1]
        else:
            self.channels[-1]['username'] = config('SECOND_CHANNEL_USERNAME', self.channels[-1]['url'])

        self.main_queue_id: str = 'mainplan'
        self.main_plan_interval: float = 10.0

        self.text = self.resourceman.text
        self.error = self.resourceman.error

        # TODO: Update these to be dynamic with languages.
        self.menu_main_keys = []
        self.menu_main: ReplyKeyboardMarkup | None = None
        self.admin_keyboard: ReplyKeyboardMarkup | None = None
        self.cancel_menu_key = []
        self.cancel_menu: ReplyKeyboardMarkup | None = None
        self.return_key = []
        self.markets_menu: ReplyKeyboardMarkup | None = None

        self.setup_main_keyboards()
        self.is_main_plan_on: bool = False

    def setup_main_keyboards(self):
        # TODO: Update these to be dynamic with languages.
        self.menu_main_keys = [
            [KeyboardButton(BotMan.Commands.CONFIG_PRICE_LIST_FA.value), KeyboardButton(BotMan.Commands.GET_FA.value)],
            [KeyboardButton(BotMan.Commands.CONFIG_CALCULATOR_FA.value),
             KeyboardButton(BotMan.Commands.CALCULATOR_FA.value)]
        ]
        self.menu_main: ReplyKeyboardMarkup = ReplyKeyboardMarkup(self.menu_main_keys, resize_keyboard=True)

        self.admin_keyboard: ReplyKeyboardMarkup = ReplyKeyboardMarkup([*self.menu_main_keys,
                                                                        [KeyboardButton(
                                                                            BotMan.Commands.ADMIN_POST_FA.value),
                                                                            KeyboardButton(
                                                                                BotMan.Commands.ADMIN_STATISTICS_FA.value)],
                                                                        [KeyboardButton(
                                                                            BotMan.Commands.ADMIN_START_SCHEDULE_FA.value),
                                                                            KeyboardButton(
                                                                                BotMan.Commands.ADMIN_STOP_SCHEDULE_FA.value)],
                                                                        ], resize_keyboard=True)

        self.cancel_menu_key = [
            [KeyboardButton(BotMan.Commands.CANCEL_FA.value)],
        ]
        self.cancel_menu: ReplyKeyboardMarkup = ReplyKeyboardMarkup(self.cancel_menu_key, resize_keyboard=True)

        self.return_key = [
            [KeyboardButton(BotMan.Commands.RETURN_FA.value)],
        ]

        self.markets_menu = ReplyKeyboardMarkup([
            [KeyboardButton(BotMan.Commands.NATIONAL_CURRENCIES_FA.value)],
            [KeyboardButton(BotMan.Commands.GOLDS_FA.value)],
            [KeyboardButton(BotMan.Commands.CRYPTOS_FA.value)], *self.return_key
        ], resize_keyboard=True)

    def mainkeyboard(self, is_admin: bool) -> ReplyKeyboardMarkup:
        return self.menu_main if not is_admin else self.admin_keyboard

    def inline_keyboard(self, list_type: Enum, button_type: Enum, all_choices: dict, selected_ones: list = None,
                        full_names: bool = False, close_button: bool = False):
        """this function creates inline keyboard for selecting/deselecting some options"""
        if not selected_ones:
            selected_ones = []
        buttons = []
        row = []
        i = 0
        for choice in all_choices:
            btn_text = choice if not full_names else all_choices[choice]
            i += 1 + int(len(btn_text) / 5)
            if choice in selected_ones:
                btn_text += "✅"
            row.append(InlineKeyboardButton(btn_text, callback_data=jsonify(
                {"lt": list_type.value, "bt": button_type.value, "v": choice})))
            if i >= 5:
                buttons.append(row)
                row = []
                i = 0
        if close_button:
            buttons.append([InlineKeyboardButton(self.resourceman.keyboard('close'), callback_data=jsonify(
                {"lt": list_type.value, "bt": button_type.value, "v": "#X"}))])
        return InlineKeyboardMarkup(buttons)

    def keyboard_from(self, language: str, *row_keys: List[str]):
        buttons = []
        for key in row_keys:
            buttons.append([self.resourceman.keyboard(key, language)])
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    async def has_subscribed_us(self, chat_id: int, context: CallbackContext) -> bool:
        chat1 = await context.bot.get_chat_member(self.channels[0]['id'], chat_id)
        chat2 = await context.bot.get_chat_member(self.channels[-1]['id'], chat_id)
        return chat1.status != ChatMember.LEFT and chat2.status != ChatMember.LEFT

    async def ask_for_subscription(self, update: Update, language: str = 'fa'):
        await update.message.reply_text(self.resourceman.text('ask_subscription_message', language) % (
            self.channels[0]['username'], self.channels[-1]['username']),
                                        reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton(self.channels[-1]['username'],
                                                                  url=self.channels[-1]['url']),
                                             InlineKeyboardButton(self.channels[0]['username'],
                                                                  url=self.channels[0]['username'])]
                                        ]))
        return None

    @property
    def currency_serv(self):
        return self.postman.currency_service

    @currency_serv.setter
    def currency_serv(self, value: CurrencyService):
        self.postman.currency_service = value

    @property
    def crypto_serv(self):
        return self.postman.crypto_service

    @crypto_serv.setter
    def crypto_serv(self, value: CryptoCurrencyService):
        self.postman.crypto_service = value

    async def next_post(self):
        return await self.postman.create_post(interval=self.main_plan_interval)
