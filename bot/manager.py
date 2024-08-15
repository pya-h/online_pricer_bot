from enum import Enum
from tools.exceptions import MaxAddedCommunityException
from decouple import config
from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, Update, CallbackQuery, Message
from telegram.ext import CallbackContext
from telegram.error import BadRequest
from api.currency_service import CurrencyService
from api.crypto_service import CryptoCurrencyService
from json import dumps as jsonify
from typing import List, Dict, Tuple, Set
from bot.post import PostMan
from models.account import Account
from models.channel import Channel, PostInterval
from tools.manuwriter import log, load_json
from tools.mathematix import persianify, cut_and_separate
from models.alarms import PriceAlarm
from tools.optifinder import OptiFinder
from .types import GroupInlineKeyboardButtonTemplate
from math import ceil as math_ceil


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
    MAXIMUM_ALLOWED_NUMBER_OF_INLINE_BUTTONS = 100
    CALLBACK_DATA_JOINER = '&'
    class Commands(Enum):
        GET_FA = resourceman.mainkeyboard('get_prices', 'fa')
        GET_EN = resourceman.mainkeyboard('get_prices', 'en')
        CALCULATOR_FA = resourceman.mainkeyboard('calculator', 'fa')
        CALCULATOR_EN = resourceman.mainkeyboard('calculator', 'en')
        CREATE_ALARM_FA = resourceman.mainkeyboard('create_alarm', 'fa')
        CREATE_ALARM_EN = resourceman.mainkeyboard('create_alarm', 'en')
        CONFIG_PRICE_LIST_FA = resourceman.mainkeyboard('config_lists')
        CONFIG_PRICE_LIST_EN = resourceman.mainkeyboard('config_lists', 'en')
        CONFIG_CALCULATOR_FA = resourceman.mainkeyboard('config_calculator', 'fa')
        CONFIG_CALCULATOR_EN = resourceman.mainkeyboard('config_calculator', 'en')
        LIST_ALARMS_FA = resourceman.mainkeyboard('list_alarms', 'fa')
        LIST_ALARMS_EN = resourceman.mainkeyboard('list_alarms', 'en')
        GO_PREMIUM_FA = resourceman.keyboard('premium', 'fa')
        GO_PREMIUM_EN = resourceman.keyboard('premium', 'en')
        SETTINGS_FA = resourceman.mainkeyboard('settings', 'fa')
        SETTINGS_EN = resourceman.mainkeyboard('settings', 'en')
        MY_PREMIUM_PLAN_DURATION_FA = resourceman.keyboard('my_premium_duration', 'fa')
        MY_PREMIUM_PLAN_DURATION_EN = resourceman.keyboard('my_premium_duration', 'en')
        MY_CHANNELS_FA = resourceman.mainkeyboard('my_channels', 'fa')
        MY_CHANNELS_EN = resourceman.mainkeyboard('my_channels', 'en')
        MY_GROUPS_FA = resourceman.mainkeyboard('my_groups', 'fa')
        MY_GROUPS_EN = resourceman.mainkeyboard('my_groups', 'en')

        CRYPTOS_FA = resourceman.keyboard('crypto', 'fa')
        CRYPTOS_EN = resourceman.keyboard('crypto', 'en')
        NATIONAL_CURRENCIES_FA = resourceman.keyboard('currency', 'fa')
        NATIONAL_CURRENCIES_EN = resourceman.keyboard('currency', 'en')
        GOLDS_FA = resourceman.keyboard('gold', 'fa')
        GOLDS_EN = resourceman.keyboard('gold', 'en')
        
        TUTORIALS_FA = resourceman.keyboard('tutorials', 'fa')
        TUTORIALS_EN = resourceman.keyboard('tutorials', 'en')
        SET_BOT_LANGUAGE_FA = resourceman.keyboard('set_language', 'fa')
        SET_BOT_LANGUAGE_EN = resourceman.keyboard('set_language', 'en')
        FACTORY_RESET_FA = resourceman.keyboard('factory_reset', 'fa')
        FACTORY_RESET_EN = resourceman.keyboard('factory_reset', 'en')
        SUPPORT_FA = resourceman.keyboard('support', 'fa')
        SUPPORT_EN = resourceman.keyboard('support', 'en')
        OUR_OTHERS_FA = resourceman.keyboard('our_others', 'fa')
        OUR_OTHERS_EN = resourceman.keyboard('our_others', 'en')

        RETURN_FA = resourceman.keyboard('return', 'fa')
        RETURN_EN = resourceman.keyboard('return', 'en')
        CANCEL_FA = resourceman.keyboard('cancel', 'fa')
        CANCEL_EN = resourceman.keyboard('cancel', 'en')

        ADMIN_NOTICES_FA = resourceman.keyboard('admin_notices', 'fa')
        ADMIN_NOTICES_EN = resourceman.keyboard('admin_notices', 'en')
        ADMIN_PLAN_CHANNEL_FA = resourceman.keyboard('admin_plan_channel', 'fa')
        ADMIN_PLAN_CHANNEL_EN = resourceman.keyboard('admin_plan_channel', 'en')
        ADMIN_STOP_CHANNEL_PLAN_FA = resourceman.keyboard('admin_stop_channel_plan', 'fa')
        ADMIN_STOP_CHANNEL_PLAN_EN = resourceman.keyboard('admin_stop_channel_plan', 'en')
        ADMIN_STATISTICS_FA = resourceman.keyboard('admin_statistics', 'fa')
        ADMIN_STATISTICS_EN = resourceman.keyboard('admin_statistics', 'en')
        ADMIN_UPGRADE_TO_PREMIUM_FA = resourceman.keyboard('admin_upgrade_to_premium', 'fa')
        ADMIN_UPGRADE_TO_PREMIUM_EN = resourceman.keyboard('admin_upgrade_to_premium', 'en')
        ADMIN_DOWNGRADE_USER_FA = resourceman.keyboard('admin_downgrade_user', 'fa')
        ADMIN_DOWNGRADE_USER_EN = resourceman.keyboard('admin_downgrade_user', 'en')
        
    class QueryActions(Enum):
        CHOOSE_LANGUAGE = 1
        SELECT_PRICE_UNIT = 2
        DISABLE_ALARM = 3
        FACTORY_RESET = 4
        SELECT_TUTORIAL = 5
        ADMIN_DOWNGRADE_USER = 6
        VERIFY_BOT_IS_ADMIN = 7
        SELECT_POST_INTERVAL = 8
        START_CHANNEL_POSTING = 9
        NONE = 0

        @staticmethod
        def Which(value: int):
            match value:
                case 1:
                    return BotMan.QueryActions.CHOOSE_LANGUAGE
                case 2:
                    return BotMan.QueryActions.SELECT_PRICE_UNIT
                case 3:
                    return BotMan.QueryActions.DISABLE_ALARM
                case 4:
                    return BotMan.QueryActions.FACTORY_RESET
                case 5:
                    return BotMan.QueryActions.SELECT_TUTORIAL
                case 6:
                    return BotMan.QueryActions.ADMIN_DOWNGRADE_USER
                case 7:
                    return BotMan.QueryActions.VERIFY_BOT_IS_ADMIN
                case 8:
                    return BotMan.QueryActions.SELECT_POST_INTERVAL
                case 9:
                    return BotMan.QueryActions.START_CHANNEL_POSTING
            return BotMan.QueryActions.NONE

    class ChatType(Enum):
            USER = 1
            CHANNEL = 2
            GROUP = 3
            NONE = 0

            @staticmethod
            def Which(value: int):
                match value:
                    case 1:
                        return BotMan.ChatType.USER
                    case 2:
                        return BotMan.ChatType.CHANNEL
                    case 3:
                        return BotMan.ChatType.GROUP
                return BotMan.ChatType.NONE

    def __init__(self, main_plan_interval: float = 10.0, plan_manager_interval: float = 1.0) -> None:
        self.resourceman = resourceman
        # environment values
        self.token: str = config('BOT_TOKEN')
        username: str = config('BOT_USERNAME')
        self.username = f"@{username}"
        self.url = f"https://t.me/{username}"

        CMC_API_KEY = config('COINMARKETCAP_API_KEY')
        CURRENCY_TOKEN = config('CURRENCY_TOKEN')
        NOBITEX_TOKEN = config('NOBITEX_TOKEN')
        ABAN_TETHER_TOKEN = config('ABAN_TETHER_TOKEN')

        self.postman = PostMan(CURRENCY_TOKEN, CMC_API_KEY, aban_tether_api_token=ABAN_TETHER_TOKEN,
                               nobitex_api_token=NOBITEX_TOKEN)

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
        self.main_plan_interval: float = main_plan_interval
        self.plan_manager_interval: float = plan_manager_interval

        self.text = self.resourceman.text
        self.error = self.resourceman.error

        self.menu_main_keys = None
        self.menu_main = None
        self.cancel_menu_key = None
        self.cancel_menu = None
        self.return_key = None

        self.setup_main_keyboards()
        self.is_main_plan_on: bool = False

    def setup_main_keyboards(self):
        self.common_menu_main_keys = [
            [KeyboardButton(BotMan.Commands.CONFIG_PRICE_LIST_FA.value), KeyboardButton(BotMan.Commands.GET_FA.value)],
            [KeyboardButton(BotMan.Commands.CONFIG_CALCULATOR_FA.value),
             KeyboardButton(BotMan.Commands.CALCULATOR_FA.value)],
            [KeyboardButton(BotMan.Commands.LIST_ALARMS_FA.value),
             KeyboardButton(BotMan.Commands.CREATE_ALARM_FA.value)],
            [KeyboardButton(BotMan.Commands.MY_GROUPS_FA.value),
             KeyboardButton(BotMan.Commands.MY_CHANNELS_FA.value)],
        ]
        self.common_menu_main_keys_en = [
            [KeyboardButton(BotMan.Commands.CONFIG_PRICE_LIST_EN.value), KeyboardButton(BotMan.Commands.GET_EN.value)],
            [KeyboardButton(BotMan.Commands.CONFIG_CALCULATOR_EN.value),
             KeyboardButton(BotMan.Commands.CALCULATOR_EN.value)],
            [KeyboardButton(BotMan.Commands.LIST_ALARMS_EN.value),
             KeyboardButton(BotMan.Commands.CREATE_ALARM_EN.value)],
            [KeyboardButton(BotMan.Commands.MY_GROUPS_EN.value),
             KeyboardButton(BotMan.Commands.MY_CHANNELS_EN.value)],
        ]

        self.cancel_menu_key = {'fa': [
            [KeyboardButton(BotMan.Commands.CANCEL_FA.value)],
        ], 'en': [
            [KeyboardButton(BotMan.Commands.CANCEL_EN.value)],
        ]}
        self.cancel_menu = lambda lang: ReplyKeyboardMarkup(self.cancel_menu_key[lang], resize_keyboard=True)

        self.return_key = {'fa': [
            [KeyboardButton(BotMan.Commands.RETURN_FA.value)],
        ], 'en': [
            [KeyboardButton(BotMan.Commands.RETURN_EN.value)],
        ]}

    def markets_menu(self, lang: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup([[KeyboardButton(BotMan.Commands.NATIONAL_CURRENCIES_FA.value)],
                                        [KeyboardButton(BotMan.Commands.GOLDS_FA.value)],
                                        [KeyboardButton(BotMan.Commands.CRYPTOS_FA.value)],
                                        *self.return_key['fa']] \
                            if lang.lower() == 'fa' else [
                                [KeyboardButton(BotMan.Commands.NATIONAL_CURRENCIES_EN.value)],
                                [KeyboardButton(BotMan.Commands.GOLDS_EN.value)],
                                [KeyboardButton(BotMan.Commands.CRYPTOS_EN.value)], *self.return_key['en']
                            ], resize_keyboard=True)


    def get_main_keyboard(self, account: Account) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup([*self.common_menu_main_keys,
                            [KeyboardButton(BotMan.Commands.GO_PREMIUM_FA.value if not account.is_premium else BotMan.Commands.MY_PREMIUM_PLAN_DURATION_FA.value), KeyboardButton(BotMan.Commands.SETTINGS_FA.value)]
                        ] if account.language != 'en' else [
                            *self.common_menu_main_keys_en,
                            [KeyboardButton(BotMan.Commands.GO_PREMIUM_EN.value if not account.is_premium else BotMan.Commands.MY_PREMIUM_PLAN_DURATION_EN.value), KeyboardButton(BotMan.Commands.SETTINGS_EN.value)]
                        ], resize_keyboard=True)
    

    def get_admin_keyboard(self, lang: str = 'fa') -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup([[KeyboardButton(
                                     BotMan.Commands.ADMIN_DOWNGRADE_USER_FA.value),
                                     KeyboardButton(
                                         BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_FA.value)],
                                 [KeyboardButton(
                                     BotMan.Commands.ADMIN_NOTICES_FA.value),
                                     KeyboardButton(
                                         BotMan.Commands.ADMIN_STATISTICS_FA.value)],
                                 [KeyboardButton(
                                     BotMan.Commands.ADMIN_PLAN_CHANNEL_FA.value),
                                     KeyboardButton(
                                         BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_FA.value)],

                                    *self.common_menu_main_keys,
                                    [KeyboardButton(BotMan.Commands.SETTINGS_FA.value)]
                                 ], resize_keyboard=True) if lang != 'en' else \
                ReplyKeyboardMarkup([[KeyboardButton(
                                     BotMan.Commands.ADMIN_DOWNGRADE_USER_EN.value),
                                     KeyboardButton(
                                         BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_EN.value)],
                                     [KeyboardButton(
                                         BotMan.Commands.ADMIN_NOTICES_EN.value),
                                         KeyboardButton(
                                             BotMan.Commands.ADMIN_STATISTICS_EN.value)],
                                     [KeyboardButton(
                                         BotMan.Commands.ADMIN_PLAN_CHANNEL_EN.value),
                                         KeyboardButton(
                                             BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_EN.value)],
                                    *self.common_menu_main_keys_en,
                                    [KeyboardButton(BotMan.Commands.SETTINGS_EN.value)]], resize_keyboard=True)


    def get_community_config_keyboard(community_type: ChatType, language: str):
        pass
    def mainkeyboard(self, account: Account) -> ReplyKeyboardMarkup:
        return self.get_main_keyboard(account) if not account.is_admin else self.get_admin_keyboard(account.language)

    @staticmethod
    def action_callback_data(action: QueryActions, value: any, page: int | None = None):
        data = {"act": action.value, "v": value}
        if page is not None:
            data['pg'] = page
        return jsonify(data)

    def inline_keyboard(self, list_type: Enum, button_type: Enum, choices: Dict[str, str],
                        selected_ones: List[str] = None, page: int = 0, max_page_buttons: int = 90,
                        full_names: bool = False, close_button: bool = False, language: str = 'fa'):
        """this function creates inline keyboard for selecting/deselecting some options"""

        def choice_callback_data(value: str | int | float | bool | None = None, page: int = 0):
            return jsonify({"lt": list_type.value if list_type else None,
                            "bt": button_type.value,
                            "pg": page,
                            "v": value})

        def special_button_callback_data(command: str | int | float | bool, page: int = 0):
            return jsonify({"lt": list_type.value if list_type else None,
                            "bt": button_type.value,
                            "pg": page,
                            "v": f"${command}"})

        if not selected_ones:
            selected_ones = []
        buttons: List[List[InlineKeyboardButton]] = []
        pagination_menu: List[InlineKeyboardButton] | None = None
        buttons_count = len(choices)
        if buttons_count > max_page_buttons:
            idx_first, idx_last = page * max_page_buttons, (page + 1) * max_page_buttons
            if idx_last > buttons_count:
                idx_last = buttons_count
            lbl_first, lbl_last = (persianify(idx_first + 1), persianify(idx_last)) if language.lower() == 'fa' else (
                idx_first + 1, idx_last)

            pages_count = int(buttons_count / max_page_buttons)
            choice_keys = list(choices.keys())[idx_first:idx_last]
            pagination_menu = [
                InlineKeyboardButton('<<', callback_data=choice_callback_data(page=0)),
                InlineKeyboardButton('<', callback_data=choice_callback_data(page=page - 1 if page > 0 else 0)),
                InlineKeyboardButton(f'({lbl_first}-{lbl_last})',
                                     callback_data=special_button_callback_data(f"#{pages_count + 1}", page)),
                InlineKeyboardButton('>', callback_data=choice_callback_data(
                    page=page + 1 if page < pages_count else int(pages_count))),
                InlineKeyboardButton('>>', callback_data=choice_callback_data(page=pages_count)),
            ]
        else:
            choice_keys = choices

        i: int = 0
        row: List[InlineKeyboardButton] = []
        for choice in choice_keys:
            btn_text = choice if not full_names else choices[choice]
            i += 1 + int(len(btn_text) / 5)
            if choice in selected_ones:
                btn_text += "✅"
            row.append(InlineKeyboardButton(btn_text, callback_data=choice_callback_data(choice, page)))
            if i >= 5:
                buttons.append(row)
                row = []
                i = 0
        if row:
            buttons.append(row)

        if pagination_menu:
            buttons.append(pagination_menu)

        if close_button:
            buttons.append(
                [InlineKeyboardButton(self.resourceman.keyboard('close'), callback_data=choice_callback_data(page=-1))])
        return InlineKeyboardMarkup(buttons)

    def inline_url(self, urls_data: List[Dict[str, str]], language: str = 'fa', columns_in_a_row: int = 2):
        """this function creates inline url keyboard for messages"""
        buttons_count = len(urls_data)
        full_rows_count = int(buttons_count / columns_in_a_row)
        buttons = [[InlineKeyboardButton(
            self.resourceman.keyboard(urls_data[col + row * columns_in_a_row]['text_key'], language),
            url=urls_data[col + row * columns_in_a_row]['url']) for col
                    in range(columns_in_a_row)] for row in range(full_rows_count)]
        full_rows_last_index = columns_in_a_row * full_rows_count
        if full_rows_last_index < buttons_count:
            buttons.append(
                [InlineKeyboardButton(self.resourceman.keyboard(urls_data[i]['text_key'], language),
                                      url=urls_data[i]['url'])
                 for i in range(full_rows_last_index, buttons_count)])
        return InlineKeyboardMarkup(buttons)

    def action_inline_keyboard(self, action: QueryActions, data: Dict[str, str], language: str = 'fa',
                               columns_in_a_row: int = 2, in_main_keyboard: bool = False):
        """this function creates inline url keyboard for messages"""
        keys = list(data.keys())
        buttons_count = len(keys)
        full_rows_count = int(buttons_count / columns_in_a_row)
        buttons = [
            [
                InlineKeyboardButton(
                    text=(self.resourceman.keyboard if not in_main_keyboard else self.resourceman.mainkeyboard)(data[keys[col + row * columns_in_a_row]], language),
                    callback_data=self.action_callback_data(action, keys[col + row * columns_in_a_row])) for col in range(columns_in_a_row)
            ] for row in range(full_rows_count)
        ]
        
        full_rows_last_index = columns_in_a_row * full_rows_count
        if full_rows_last_index < buttons_count:
            buttons.append(
                [
                    InlineKeyboardButton(self.resourceman.keyboard(data[keys[i]], language), callback_data=self.action_callback_data(action, keys[i])) \
                        for i in range(full_rows_last_index, buttons_count)
                ]
            )
        return InlineKeyboardMarkup(buttons)

    def users_list_menu(self, users: List[Account], list_type: QueryActions, columns_in_a_row: int = 3, page: int = 0, max_page_buttons: int = 90, language: str = 'fa'):
        """this function creates inline keyboard for users data as callback data"""
        buttons_count = len(users)

        pagination_menu: List[InlineKeyboardButton] | None = None
        pagination_callback_data = lambda page: self.action_callback_data(list_type, None, page)

        if buttons_count > max_page_buttons:
            idx_first, idx_last = page * max_page_buttons, (page + 1) * max_page_buttons
            if idx_last > buttons_count:
                idx_last = buttons_count
            lbl_first, lbl_last = (persianify(idx_first + 1), persianify(idx_last)) if language.lower() == 'fa' else (
                idx_first + 1, idx_last)

            pages_count = int(buttons_count / max_page_buttons)
            users = list(users)[idx_first:idx_last]
            pagination_menu = [
                InlineKeyboardButton('<<', callback_data=pagination_callback_data(0)),
                InlineKeyboardButton('<', callback_data=pagination_callback_data(page=page - 1 if page > 0 else 0)),
                InlineKeyboardButton(f'({lbl_first}-{lbl_last})', callback_data=pagination_callback_data(page)),
                InlineKeyboardButton('>', callback_data=pagination_callback_data(
                    page=page + 1 if page < pages_count else int(pages_count))),
                InlineKeyboardButton('>>', callback_data=pagination_callback_data(pages_count)),
            ]

            buttons_count = len(users)

        full_rows_count = int(buttons_count / columns_in_a_row)

        buttons = [
            [
                InlineKeyboardButton(text=str(users[col + row * columns_in_a_row]),
                            callback_data=self.action_callback_data(list_type, users[col + row * columns_in_a_row].chat_id)) for col in range(columns_in_a_row)
            ] for row in range(full_rows_count)
        ]
        
        full_rows_last_index = columns_in_a_row * full_rows_count
        if full_rows_last_index < buttons_count:
            buttons.append(
                [
                    InlineKeyboardButton(text=str(users[i]), callback_data=self.action_callback_data(list_type, users[i].chat_id)) for i in range(full_rows_last_index, buttons_count)
                ]
            )
        if pagination_menu:
            buttons.append(pagination_menu)

        buttons.append(
                [InlineKeyboardButton(self.resourceman.keyboard('close'), callback_data=pagination_callback_data(-1))])
        return InlineKeyboardMarkup(buttons)

    def keyboard_from(self, language: str, *row_keys: List[str]):
        buttons = []
        for key in row_keys:
            buttons.append([self.resourceman.keyboard(key, language)])
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    async def has_subscribed_us(self, chat_id: int, context: CallbackContext) -> bool:
        try:
            chat1 = await context.bot.get_chat_member(self.channels[0]['id'], chat_id)
            chat2 = await context.bot.get_chat_member(self.channels[-1]['id'], chat_id)
        except BadRequest as ex:
            log('Can not determine channel membership, seems the bot is not an admin in specified channels.', ex)
            await self.inform_admins('bot_not_channel_admin', context, is_error=True)
            return False
        return chat1.status != ChatMember.LEFT and chat2.status != ChatMember.LEFT

    async def inform_admins(self, message_key: str, context: CallbackContext, is_error: bool = False):
        message_text = self.error if is_error else self.text
        for admin in Account.GetAdmins(just_hardcode_admin=False):
            try:
                await context.bot.send_message(chat_id=admin.chat_id, text=message_text(message_key, admin.language))
            except:
                pass

    async def ask_for_subscription(self, update: Update, language: str = 'fa'):
        await update.message.reply_text(self.resourceman.text('ask_subscription_message', language) % (
            self.channels[0]['username'], self.channels[-1]['username']),
                                        reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton(self.channels[-1]['username'],
                                                                  url=self.channels[-1]['url']),
                                             InlineKeyboardButton(self.channels[0]['username'],
                                                                  url=self.channels[0]['url'])]
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

    def check_price_alarms(self) -> List[PriceAlarm]:
        """Checks all user alarms and finds alarms that has gone off"""
        print('ALARM CHECK:')
        alarms = PriceAlarm.Get()
        # TODO: Define a pre_latest_data, check for currencies that have changed in 10m and then get alarms by currencies
        triggered_alarms = []
        for alarm in alarms:
            print(alarm)
            source = self.currency_serv
            alarm.current_price = self.currency_serv.get_single_price(alarm.currency, alarm.target_unit)
            if alarm.current_price is None:
                alarm.current_price = self.crypto_serv.get_single_price(alarm.currency, alarm.target_unit)
                source = self.crypto_serv

            if alarm.current_price is not None:
                alarm.full_currency_name = {'en': alarm.currency.upper(),
                                            'fa': source.GetPersianName(alarm.currency.upper())}
                match alarm.change_direction:
                    case PriceAlarm.ChangeDirection.UP:
                        if alarm.current_price >= alarm.target_price:
                            triggered_alarms.append(alarm)

                    case PriceAlarm.ChangeDirection.DOWN:
                        if alarm.current_price <= alarm.target_price:
                            triggered_alarms.append(alarm)

                    case _:
                        if alarm.current_price == alarm.target_price:
                            triggered_alarms.append(alarm)
        print(triggered_alarms)
        return triggered_alarms

    async def handle_possible_alarms(self, send_message_func):
        # start notifying users [if at least one alarm went off]
        unit_names = {
            'IRT': {'fa': self.currency_serv.GetPersianName('IRT'), 'en': 'IRT'},
            'USD': {'fa': self.currency_serv.GetPersianName('USD'), 'en': 'USD'}
        }
        for alarm in self.check_price_alarms():
            try:
                account = Account.GetById(alarm.chat_id, prevent_instance_arrangement=True)
                target_price = cut_and_separate(alarm.target_price)
                current_price = cut_and_separate(alarm.current_price)
                currency_name, unit_name = alarm.full_currency_name[account.language], unit_names[alarm.target_unit][
                    account.language]

                if account.language == 'fa':
                    target_price, current_price = persianify(target_price), persianify(current_price)
                price_alarm_text = self.text('price_alarm', account.language) % (
                    currency_name, target_price, unit_name) + \
                                   self.text('current_price_is', account.language) % (
                                       currency_name, current_price, unit_name)
                await send_message_func(chat_id=account.chat_id, text=price_alarm_text)
                alarm.disable()
            except:
                pass

    async def show_reached_max_error(self, telegram_handle: Update | CallbackQuery, account: Account, max_value: int):
        if not account.is_premium:
            link = f"https://t.me/{Account.GetHardcodeAdmin()['username']}"
            await telegram_handle.message.reply_text(
                text=self.error('max_selection', account.language) % (max_value,) + self.error('get_premium', account.language),
                reply_markup=self.inline_url([{'text_key': "premium", 'url': link}])
            )
        else:
            await telegram_handle.message.reply_text(text=self.error('max_selection', account.language) % (max_value,))

    async def show_settings_menu(self, update: Update):
        account = Account.Get(update.message.chat)
        keyboard = ReplyKeyboardMarkup([[KeyboardButton(BotMan.Commands.TUTORIALS_FA.value)], [KeyboardButton(BotMan.Commands.FACTORY_RESET_FA.value), KeyboardButton(BotMan.Commands.SET_BOT_LANGUAGE_FA.value)],
                                    [KeyboardButton(BotMan.Commands.OUR_OTHERS_FA.value), KeyboardButton(BotMan.Commands.SUPPORT_FA.value)], [KeyboardButton(BotMan.Commands.RETURN_FA.value)]] if account.language.lower() == 'fa' else \
                                        [[KeyboardButton(BotMan.Commands.TUTORIALS_EN.value)], [KeyboardButton(BotMan.Commands.FACTORY_RESET_EN.value), KeyboardButton(BotMan.Commands.SET_BOT_LANGUAGE_EN.value)],
                                    [KeyboardButton(BotMan.Commands.OUR_OTHERS_EN.value), KeyboardButton(BotMan.Commands.SUPPORT_EN.value)], [KeyboardButton(BotMan.Commands.RETURN_EN.value)]], resize_keyboard=True, one_time_keyboard=False)
        return await update.message.reply_text(self.resourceman.mainkeyboard('settings', account.language), reply_markup=keyboard)
    

    async def clear_unwanted_menu_messages(self, update: Update, context: CallbackContext, operation_result):
        if isinstance(operation_result, Message):
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=operation_result.message_id )
        await update.message.delete()

    async def list_premiums(self, update: Update, list_type: QueryActions) -> bool:
        account = Account.Get(update.message.chat)
        premiums = Account.GetPremiumUsers()
        if not premiums:
            await update.message.reply_text(text=self.text('no_premium_users_found', account.language), reply_markup=self.mainkeyboard(account))
            return False
        menu = self.users_list_menu(premiums, list_type, columns_in_a_row=3, page=0, language=account.language)

        await update.message.reply_text(text=self.text('select_user', account.language), reply_markup=menu)
        return True
    
    def identify_user(self, update: Update) -> Account | None:
        '''Get the user's Account object from update object by one of these methods:
            1- providing a forwarded message from the desired user
            2- providing the username of the user
            3- providing the chat_id of the user.
        '''
        user: Account | None = None
        if update.message.forward_from:
            upgrading_chat_id = update.message.forward_from.id
            user = Account.GetById(upgrading_chat_id)
            user.current_username = update.message.forward_from.username
            user.firstname = update.message.forward_from.first_name
        elif update.message.text[0] == '@':
            try:
                user = Account.GetByUsername(update.message.text)
                if user:
                    upgrading_chat_id = user.chat_id
            except:
                upgrading_chat_id = None
        else:
            try:
                upgrading_chat_id = int(update.message.text)
                user = Account.GetById(upgrading_chat_id)
            except:
                upgrading_chat_id = None
        return user

    def extract_coef(self, word: str | float):
        try:
            f = float(word)
            intf = int(f)
            return f if intf != f else intf 
        except:
            pass
        return 1
    
    def extract_symbols_and_amounts(self, text: str) -> Tuple[Set[str], Set[str]]:
        words = text.split()
        crypto_amounts = set()
        currency_amounts = set()

        finder = OptiFinder(words)
        i = 0

        while i < finder.word_count:
            words[i] = words[i].upper()
            prev_word: str | float = words[i - 1] if i else 1.0
            slug, word_count = finder.search_around(self.crypto_serv.CoinsInPersian, i)
            if slug:
                coef = self.extract_coef(prev_word)
                crypto_amounts.add(f'{coef} {slug}')
            else:
                slug, word_count = finder.search_around(self.currency_serv.CurrenciesInPersian, i)
                
                if not slug:
                    slug, word_count = finder.search_around(self.currency_serv.PersianShortcuts)

                if slug:
                    coef = self.extract_coef(prev_word)
                    currency_amounts.add(f'{coef} {slug}')
            i += word_count
        return crypto_amounts, currency_amounts
    
    def create_crypto_equalize_message(self, unit: str, amount: float | int, target_cryptos: List[str] | None, target_currencies: List[str] | None, language: str = 'fa'):
        header, response, _, absolute_irt = self.crypto_serv.equalize(unit, amount, target_cryptos)
        response = self.currency_serv.irt_to_currencies(absolute_irt, unit, target_currencies) + "\n\n" + response
        return header + response
    
    def create_currency_equalize_message(self, unit: str, amount: float | int, target_cryptos: List[str] | None, target_currencies: List[str] | None, language: str = 'fa'):
        header, response, absolute_usd, _ = self.currency_serv.equalize(unit, amount, target_currencies)
        response += "\n\n" + self.crypto_serv.usd_to_cryptos(absolute_usd, unit, target_cryptos)
        return header + response
    
    @staticmethod
    def ArrangeInlineKeyboardButtons(list_of_keys: list[GroupInlineKeyboardButtonTemplate], query_action: QueryActions):
        keys_count = len(list_of_keys)
        keys = [[InlineKeyboardButton(list_of_keys[j].title, callback_data=BotMan.action_callback_data(query_action, list_of_keys[j].value)) \
                 for j in range(i * 5, (i + 1) * 5 if (i + 1) * 5 < keys_count else keys_count)] \
                    for i in range(math_ceil(keys_count // 5))]

        return InlineKeyboardMarkup(keys)
    
    async def prepare_channel(self, ctx: CallbackContext, owner: Account, channel_id: int, interval: int):
        try:
            channel_response: Message = await ctx.bot.send_message(chat_id=channel_id, text="OK")
            await ctx.bot.delete_message(chat_id=channel_id, message_id=channel_response.message_id)
            channel = Channel(channel_id, owner.chat_id, int(interval), channel_response.chat.username or None, channel_response.chat.title or 'Unnamed')
            channel.create()
            post_interval, desc_en, desc_fa = PostInterval(minutes=interval).timestamps
            interval_description: str = None
            if owner.language.lower() == 'fa':
                post_interval = persianify(post_interval)
                interval_description = persianify(desc_fa)
            else:
                interval_description = desc_en
            
            await ctx.bot.send_message(chat_id=owner.chat_id, text=self.text("click_to_start_channel_posting", owner.language) % (post_interval, interval_description),
                                    reply_markup=self.action_inline_keyboard(self.QueryActions.START_CHANNEL_POSTING, {channel_id: "start"}, owner.language, columns_in_a_row=1))
        except MaxAddedCommunityException:
            await ctx.bot.send_message(chat_id=owner.chat_id, text=self.error("max_channels_reached", owner.language))
            return False
        except Exception as ex:
            log("Getting and planning channel data failed.", ex, category_name="Channels")
            return False
        return True