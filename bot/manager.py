from enum import Enum
from tools.exceptions import (
    MaxAddedCommunityException,
    InvalidInputException,
    NoSuchThingException,
)
from decouple import config
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
    Update,
    CallbackQuery,
    Message,
    Chat,
)
from telegram.ext import CallbackContext
from telegram.error import BadRequest, Forbidden
from api.currency_service import CurrencyService
from api.crypto_service import CryptoCurrencyService
from json import dumps as jsonify
from typing import List, Dict, Tuple, Set, Coroutine, Any, Callable
from bot.post import PostMan
from models.account import Account
from models.channel import Channel, PostInterval
from models.group import Group
from tools.manuwriter import log, load_json
from tools.mathematix import (
    persianify,
    cut_and_separate,
    now_in_minute,
    tz_today,
    extract_thousands,
    normal_float_display,
)
from models.alarms import PriceAlarm
from tools.optifinder import OptiFinder
from .types import (
    GroupInlineKeyboardButtonTemplate,
    SelectionListTypes,
    MarketOptions,
    ResourceManager,
)
from math import ceil as math_ceil
from .settings import BotSettings
import asyncio


resourceman = ResourceManager("texts", "resources")


class BotMan:
    """This class is defined to collect all common and handy options, fields and features of online pricer bot"""

    MAXIMUM_ALLOWED_NUMBER_OF_INLINE_BUTTONS = 100
    CALLBACK_DATA_DELIMITER = "&"

    class Commands(Enum):
        GET_FA = resourceman.mainkeyboard("get_prices", "fa")
        GET_EN = resourceman.mainkeyboard("get_prices", "en")
        CALCULATOR_FA = resourceman.mainkeyboard("calculator", "fa")
        CALCULATOR_EN = resourceman.mainkeyboard("calculator", "en")
        CREATE_ALARM_FA = resourceman.mainkeyboard("create_alarm", "fa")
        CREATE_ALARM_EN = resourceman.mainkeyboard("create_alarm", "en")
        CONFIG_PRICE_LIST_FA = resourceman.mainkeyboard("config_lists")
        CONFIG_PRICE_LIST_EN = resourceman.mainkeyboard("config_lists", "en")
        CONFIG_CALCULATOR_FA = resourceman.mainkeyboard("config_calculator", "fa")
        CONFIG_CALCULATOR_EN = resourceman.mainkeyboard("config_calculator", "en")
        LIST_ALARMS_FA = resourceman.mainkeyboard("list_alarms", "fa")
        LIST_ALARMS_EN = resourceman.mainkeyboard("list_alarms", "en")
        GO_PREMIUM_FA = resourceman.keyboard("premium", "fa")
        GO_PREMIUM_EN = resourceman.keyboard("premium", "en")
        SETTINGS_FA = resourceman.mainkeyboard("settings", "fa")
        SETTINGS_EN = resourceman.mainkeyboard("settings", "en")
        MY_PREMIUM_PLAN_DURATION_FA = resourceman.keyboard("my_premium_duration", "fa")
        MY_PREMIUM_PLAN_DURATION_EN = resourceman.keyboard("my_premium_duration", "en")
        MY_CHANNELS_FA = resourceman.mainkeyboard("my_channels", "fa")
        MY_CHANNELS_EN = resourceman.mainkeyboard("my_channels", "en")
        MY_GROUPS_FA = resourceman.mainkeyboard("my_groups", "fa")
        MY_GROUPS_EN = resourceman.mainkeyboard("my_groups", "en")

        CRYPTOS_FA = resourceman.keyboard("crypto", "fa")
        CRYPTOS_EN = resourceman.keyboard("crypto", "en")
        NATIONAL_CURRENCIES_FA = resourceman.keyboard("currency", "fa")
        NATIONAL_CURRENCIES_EN = resourceman.keyboard("currency", "en")
        GOLDS_FA = resourceman.keyboard("gold", "fa")
        GOLDS_EN = resourceman.keyboard("gold", "en")

        TUTORIALS_FA = resourceman.keyboard("tutorials", "fa")
        TUTORIALS_EN = resourceman.keyboard("tutorials", "en")
        SET_BOT_LANGUAGE_FA = resourceman.keyboard("set_language", "fa")
        SET_BOT_LANGUAGE_EN = resourceman.keyboard("set_language", "en")
        FACTORY_RESET_FA = resourceman.keyboard("factory_reset", "fa")
        FACTORY_RESET_EN = resourceman.keyboard("factory_reset", "en")
        SUPPORT_FA = resourceman.keyboard("support", "fa")
        SUPPORT_EN = resourceman.keyboard("support", "en")
        OUR_OTHERS_FA = resourceman.keyboard("our_others", "fa")
        OUR_OTHERS_EN = resourceman.keyboard("our_others", "en")

        CHANNELS_CHANGE_INTERVAL_FA = resourceman.keyboard("channels_change_interval", "fa")
        CHANNELS_CHANGE_INTERVAL_EN = resourceman.keyboard("channels_change_interval", "en")
        COMMUNITY_CONFIG_PRICE_LIST_FA = resourceman.keyboard("community_config_price_list", "fa")
        COMMUNITY_CONFIG_PRICE_LIST_EN = resourceman.keyboard("community_config_price_list", "en")
        COMMUNITY_TRIGGER_DATE_TAG_FA = resourceman.keyboard("community_trigger_date_tag", "fa")
        COMMUNITY_TRIGGER_DATE_TAG_EN = resourceman.keyboard("community_trigger_date_tag", "en")
        COMMUNITY_TRIGGER_MARKET_TAGS_FA = resourceman.keyboard("community_trigger_market_tags", "fa")
        COMMUNITY_TRIGGER_MARKET_TAGS_EN = resourceman.keyboard("community_trigger_market_tags", "en")
        COMMUNITY_SET_MESSAGE_HEADER_FA = resourceman.keyboard("community_set_message_header", "fa")
        COMMUNITY_SET_MESSAGE_HEADER_EN = resourceman.keyboard("community_set_message_header", "en")
        COMMUNITY_SET_MESSAGE_FOOTNOTE_FA = resourceman.keyboard("community_set_message_footnote", "fa")
        COMMUNITY_SET_MESSAGE_FOOTNOTE_EN = resourceman.keyboard("community_set_message_footnote", "en")
        CHANNEL_CHANGE_FA = resourceman.keyboard("channel_change", "fa")
        CHANNEL_CHANGE_EN = resourceman.keyboard("channel_change", "en")
        GROUP_CHANGE_FA = resourceman.keyboard("change_group", "fa")
        GROUP_CHANGE_EN = resourceman.keyboard("change_group", "en")
        COMMUNITY_DISCONNECT_FA = resourceman.keyboard("community_disconnect", "fa")
        COMMUNITY_DISCONNECT_EN = resourceman.keyboard("community_disconnect", "en")

        RETURN_FA = resourceman.keyboard("return", "fa")
        RETURN_EN = resourceman.keyboard("return", "en")
        CANCEL_FA = resourceman.keyboard("cancel", "fa")
        CANCEL_EN = resourceman.keyboard("cancel", "en")

        ADMIN_UPGRADE_TO_PREMIUM_FA = resourceman.keyboard("admin_upgrade_to_premium", "fa")
        ADMIN_UPGRADE_TO_PREMIUM_EN = resourceman.keyboard("admin_upgrade_to_premium", "en")
        ADMIN_DOWNGRADE_USER_FA = resourceman.keyboard("admin_downgrade_user", "fa")
        ADMIN_DOWNGRADE_USER_EN = resourceman.keyboard("admin_downgrade_user", "en")

        GOD_ADD_ADMIN_FA = resourceman.keyboard("add_admin", "fa")
        GOD_ADD_ADMIN_EN = resourceman.keyboard("add_admin", "en")
        GOD_REMOVE_ADMIN_FA = resourceman.keyboard("remove_admin", "fa")
        GOD_REMOVE_ADMIN_EN = resourceman.keyboard("remove_admin", "en")
        GOD_NOTICES_FA = resourceman.keyboard("admin_notices", "fa")
        GOD_NOTICES_EN = resourceman.keyboard("admin_notices", "en")
        GOD_STATISTICS_FA = resourceman.keyboard("admin_statistics", "fa")
        GOD_STATISTICS_EN = resourceman.keyboard("admin_statistics", "en")
        GOD_CHANGE_PREMIUM_PLANS_FA = resourceman.keyboard("change_premium_plans", "fa")
        GOD_CHANGE_PREMIUM_PLANS_EN = resourceman.keyboard("change_premium_plans", "en")

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
        TRIGGER_DATE_TAG = 10
        TRIGGER_MARKET_TAGS = 11
        UPDATE_MESSAGE_SECTIONS = 12
        DISCONNECT_COMMUNITY = 13
        REQUEST_RECONNECT_COMMUNITY = 14
        RECONNECT_COMMUNITY = 15
        LIST_ENTITY = 16
        IVE_SUBSCRIBED = 17
        REMOVE_ADMIN = 18
        NONE = 0

        @staticmethod
        def which(value: int):
            try:
                return BotMan.QueryActionOptions[int(value)]
            except:
                pass
            return Account.States.NONE

    QueryActionOptions = (
        QueryActions.NONE,
        QueryActions.CHOOSE_LANGUAGE,
        QueryActions.SELECT_PRICE_UNIT,
        QueryActions.DISABLE_ALARM,
        QueryActions.FACTORY_RESET,
        QueryActions.SELECT_TUTORIAL,
        QueryActions.ADMIN_DOWNGRADE_USER,
        QueryActions.VERIFY_BOT_IS_ADMIN,
        QueryActions.SELECT_POST_INTERVAL,
        QueryActions.START_CHANNEL_POSTING,
        QueryActions.TRIGGER_DATE_TAG,
        QueryActions.TRIGGER_MARKET_TAGS,
        QueryActions.UPDATE_MESSAGE_SECTIONS,
        QueryActions.DISCONNECT_COMMUNITY,
        QueryActions.REQUEST_RECONNECT_COMMUNITY,
        QueryActions.RECONNECT_COMMUNITY,
        QueryActions.LIST_ENTITY,
        QueryActions.IVE_SUBSCRIBED,
        QueryActions.REMOVE_ADMIN
    )

    class CommunityType(Enum):
        CHANNEL = 1
        GROUP = 2
        NONE = 0

        @staticmethod
        def which(value: int):
            match value:
                case BotMan.CommunityType.CHANNEL.value:
                    return BotMan.CommunityType.CHANNEL
                case BotMan.CommunityType.GROUP.value:
                    return BotMan.CommunityType.GROUP
            return BotMan.CommunityType.NONE

        def __str__(self) -> str:
            return self.toString(self.value)

        @staticmethod
        def toString(value: int) -> str:
            return (
                "channel"
                if value == BotMan.CommunityType.CHANNEL.value
                else "group" if value == BotMan.CommunityType.GROUP.value else "none"
            )

        @staticmethod
        def toClass(value: int) -> Channel | Group | None:
            return Channel if value == BotMan.CommunityType.CHANNEL.value else Group if value == BotMan.CommunityType.GROUP.value else None

        def to_class(self) -> Channel | Group | None:
            return self.toClass(self.value)

    class MenuSections(Enum):
        COMMUNITY_PANEL = 1
        NONE = 0

        @staticmethod
        def which(value: int):
            match value:
                case BotMan.MenuSections.COMMUNITY_PANEL.value:
                    return BotMan.MenuSections.COMMUNITY_PANEL
            return BotMan.MenuSections.NONE

    def __init__(self, main_plan_interval: float | None = None, plan_manager_interval: float = 1.0) -> None:
        self.resourceman = resourceman
        # environment values
        self.token: str = config("BOT_TOKEN")
        username: str = config("BOT_USERNAME")
        self.username = f"@{username}"
        self.url = f"https://t.me/{username}"
        self.host_url = config("HOST_URL")
        self.bot_tag = config("BOT_TAG")
        self.bot_port = int(config("BOT_PORT"))

        self.postman = PostMan(
            resourceman,
            source_arena_api_key=config("CURRENCY_TOKEN", cast=str),
            coinmarketcap_api_key=config("COINMARKETCAP_API_KEY", cast=str),
            nobitex_api_token=config("NOBITEX_TOKEN", cast=str),
            aban_tether_api_token=config("ABAN_TETHER_TOKEN", cast=str),
        )

        self.channels = [
            {"id": config("CHANNEL_ID"), "url": config("CHANNEL_URL")},
            {
                "id": config("SECOND_CHANNEL_ID", None),
                "url": config("SECOND_CHANNEL_URL", None),
            },
        ]

        self.channels[0]["username"] = config("CHANNEL_USERNAME", self.channels[0]["url"])
        if not self.channels[1]["id"]:
            del self.channels[1]
        else:
            self.channels[-1]["username"] = config("SECOND_CHANNEL_USERNAME", self.channels[-1]["url"])

        self.main_queue_id: str = "mainplan"
        self.main_plan_interval: float = main_plan_interval or float(config('MAIN_CHANNEL_DEFAULT_INTERVAL', 10.0))
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
        self.last_daily_check: int | None = None
        BotSettings.init()

    def setup_main_keyboards(self):
        self.common_menu_main_keys = [
            [
                KeyboardButton(BotMan.Commands.CONFIG_PRICE_LIST_FA.value),
                KeyboardButton(BotMan.Commands.GET_FA.value),
            ],
            [
                KeyboardButton(BotMan.Commands.CONFIG_CALCULATOR_FA.value),
                KeyboardButton(BotMan.Commands.CALCULATOR_FA.value),
            ],
            [
                KeyboardButton(BotMan.Commands.LIST_ALARMS_FA.value),
                KeyboardButton(BotMan.Commands.CREATE_ALARM_FA.value),
            ],
            [
                KeyboardButton(BotMan.Commands.MY_GROUPS_FA.value),
                KeyboardButton(BotMan.Commands.MY_CHANNELS_FA.value),
            ],
        ]
        self.common_menu_main_keys_en = [
            [
                KeyboardButton(BotMan.Commands.CONFIG_PRICE_LIST_EN.value),
                KeyboardButton(BotMan.Commands.GET_EN.value),
            ],
            [
                KeyboardButton(BotMan.Commands.CONFIG_CALCULATOR_EN.value),
                KeyboardButton(BotMan.Commands.CALCULATOR_EN.value),
            ],
            [
                KeyboardButton(BotMan.Commands.LIST_ALARMS_EN.value),
                KeyboardButton(BotMan.Commands.CREATE_ALARM_EN.value),
            ],
            [
                KeyboardButton(BotMan.Commands.MY_GROUPS_EN.value),
                KeyboardButton(BotMan.Commands.MY_CHANNELS_EN.value),
            ],
        ]

        self.cancel_menu_key = {
            "fa": [
                [KeyboardButton(BotMan.Commands.CANCEL_FA.value)],
            ],
            "en": [
                [KeyboardButton(BotMan.Commands.CANCEL_EN.value)],
            ],
        }
        self.cancel_menu = lambda lang: ReplyKeyboardMarkup(self.cancel_menu_key[lang.lower()], resize_keyboard=True)

        self.return_key = {
            "fa": [
                [KeyboardButton(BotMan.Commands.RETURN_FA.value)],
            ],
            "en": [
                [KeyboardButton(BotMan.Commands.RETURN_EN.value)],
            ],
        }

    def markets_menu(self, lang: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            (
                [
                    [KeyboardButton(BotMan.Commands.NATIONAL_CURRENCIES_FA.value)],
                    [KeyboardButton(BotMan.Commands.GOLDS_FA.value)],
                    [KeyboardButton(BotMan.Commands.CRYPTOS_FA.value)],
                    *self.return_key["fa"],
                ]
                if lang != "en"
                else [
                    [KeyboardButton(BotMan.Commands.NATIONAL_CURRENCIES_EN.value)],
                    [KeyboardButton(BotMan.Commands.GOLDS_EN.value)],
                    [KeyboardButton(BotMan.Commands.CRYPTOS_EN.value)],
                    *self.return_key["en"],
                ]
            ),
            resize_keyboard=True,
        )

    def get_normal_primary_keyboard(self, account: Account) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            (
                [
                    *self.common_menu_main_keys,
                    [
                        KeyboardButton(
                            BotMan.Commands.GO_PREMIUM_FA.value
                            if not account.is_premium
                            else BotMan.Commands.MY_PREMIUM_PLAN_DURATION_FA.value
                        ),
                        KeyboardButton(BotMan.Commands.SETTINGS_FA.value),
                    ],
                ]
                if account.language != "en"
                else [
                    *self.common_menu_main_keys_en,
                    [
                        KeyboardButton(
                            BotMan.Commands.GO_PREMIUM_EN.value
                            if not account.is_premium
                            else BotMan.Commands.MY_PREMIUM_PLAN_DURATION_EN.value
                        ),
                        KeyboardButton(BotMan.Commands.SETTINGS_EN.value),
                    ],
                ]
            ),
            resize_keyboard=True,
        )

    def get_admin_primary_keyboard(self, account: Account) -> ReplyKeyboardMarkup:
        return (
            ReplyKeyboardMarkup(
                [
                    [
                        KeyboardButton(BotMan.Commands.ADMIN_DOWNGRADE_USER_FA.value),
                        KeyboardButton(BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_FA.value),
                    ],
                    *(
                        [
                            [
                                KeyboardButton(BotMan.Commands.GOD_NOTICES_FA.value),
                                KeyboardButton(BotMan.Commands.GOD_STATISTICS_FA.value),
                            ],
                            *self.common_menu_main_keys,
                            [
                                KeyboardButton(BotMan.Commands.GOD_CHANGE_PREMIUM_PLANS_FA.value),
                                KeyboardButton(BotMan.Commands.SETTINGS_FA.value),
                            ]
                        ] if account.is_god else self.common_menu_main_keys
                    )
                ],
                resize_keyboard=True,
            ) if account.language != "en"
            else ReplyKeyboardMarkup(
                [
                    [
                        KeyboardButton(BotMan.Commands.ADMIN_DOWNGRADE_USER_EN.value),
                        KeyboardButton(BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_EN.value),
                    ],
                    *(
                        [
                            [
                                KeyboardButton(BotMan.Commands.GOD_NOTICES_EN.value),
                                KeyboardButton(BotMan.Commands.GOD_STATISTICS_EN.value),
                            ],
                            *self.common_menu_main_keys_en,
                            [
                                KeyboardButton(BotMan.Commands.GOD_CHANGE_PREMIUM_PLANS_EN.value),
                                KeyboardButton(BotMan.Commands.SETTINGS_EN.value),
                            ]
                        ] if account.is_god else self.common_menu_main_keys_en
                    )
                ],
                resize_keyboard=True,
            )
        )

    def get_community_config_keyboard(self, community_type: CommunityType, language: str):
        if community_type == self.CommunityType.CHANNEL:
            return ReplyKeyboardMarkup(
                (
                    [
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_CONFIG_PRICE_LIST_FA.value),
                            KeyboardButton(BotMan.Commands.CHANNELS_CHANGE_INTERVAL_FA.value),
                        ],
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_MARKET_TAGS_FA.value),
                            KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_DATE_TAG_FA.value),
                        ],
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_FA.value),
                            KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_HEADER_FA.value),
                        ],
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_DISCONNECT_FA.value),
                            KeyboardButton(BotMan.Commands.CHANNEL_CHANGE_FA.value),
                        ],
                        [KeyboardButton(BotMan.Commands.RETURN_FA.value)],
                    ]
                    if language != "en"
                    else [
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_CONFIG_PRICE_LIST_EN.value),
                            KeyboardButton(BotMan.Commands.CHANNELS_CHANGE_INTERVAL_EN.value),
                        ],
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_MARKET_TAGS_EN.value),
                            KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_DATE_TAG_EN.value),
                        ],
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_EN.value),
                            KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_HEADER_EN.value),
                        ],
                        [
                            KeyboardButton(BotMan.Commands.COMMUNITY_DISCONNECT_EN.value),
                            KeyboardButton(BotMan.Commands.CHANNEL_CHANGE_EN.value),
                        ],
                        [KeyboardButton(BotMan.Commands.RETURN_EN.value)],
                    ]
                ),
                resize_keyboard=True,
            )
        return ReplyKeyboardMarkup(
            (
                [
                    [KeyboardButton(BotMan.Commands.COMMUNITY_CONFIG_PRICE_LIST_FA.value)],
                    [
                        KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_MARKET_TAGS_FA.value),
                        KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_DATE_TAG_FA.value),
                    ],
                    [
                        KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_FA.value),
                        KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_HEADER_FA.value),
                    ],
                    [
                        KeyboardButton(BotMan.Commands.COMMUNITY_DISCONNECT_FA.value),
                        KeyboardButton(BotMan.Commands.GROUP_CHANGE_FA.value),
                    ],
                    [KeyboardButton(BotMan.Commands.RETURN_FA.value)],
                ]
                if language != "en"
                else [
                    [
                        KeyboardButton(BotMan.Commands.COMMUNITY_CONFIG_PRICE_LIST_EN.value),
                    ],
                    [
                        KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_MARKET_TAGS_EN.value),
                        KeyboardButton(BotMan.Commands.COMMUNITY_TRIGGER_DATE_TAG_EN.value),
                    ],
                    [
                        KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_EN.value),
                        KeyboardButton(BotMan.Commands.COMMUNITY_SET_MESSAGE_HEADER_EN.value),
                    ],
                    [
                        KeyboardButton(BotMan.Commands.COMMUNITY_DISCONNECT_EN.value),
                        KeyboardButton(BotMan.Commands.GROUP_CHANGE_EN.value),
                    ],
                    [KeyboardButton(BotMan.Commands.RETURN_EN.value)],
                ]
            ),
            resize_keyboard=True,
        )

    def mainkeyboard(self, account: Account) -> ReplyKeyboardMarkup:
        return self.get_normal_primary_keyboard(account) if not account.is_admin else self.get_admin_primary_keyboard(account)

    @staticmethod
    def actionCallbackData(action: QueryActions, value: any, page: int | None = None):
        data = {"act": action.value, "v": value}
        if page is not None:
            data["pg"] = page
        return jsonify(data)

    @staticmethod
    def inlineKeyboardChoiceCallbackData(list_type: Enum, button_type: Enum, value: str | int | float | bool | None = None, page: int = 0):
        return jsonify(
            {
                "lt": list_type.value if list_type else None,
                "bt": button_type.value,
                "pg": page,
                "v": value,
            }
        )

    def inline_keyboard(
        self,
        list_type: Enum,
        button_type: Enum,
        choices: Dict[str, str],
        selected_ones: List[str] | List[str] = None,
        page: int = 0,
        max_page_buttons: int = 90,
        close_button: bool = False,
        language: str = "fa",
        choices_start_offset: int = 0,
    ):
        """this function creates inline keyboard for selecting/deselecting some options"""
        if not selected_ones:
            selected_ones = []
        buttons: List[List[InlineKeyboardButton]] = []
        pagination_menu: List[InlineKeyboardButton] | None = None
        buttons_count = len(choices)

        if buttons_count > max_page_buttons:
            idx_first, idx_last = page * max_page_buttons, (page + 1) * max_page_buttons
            if idx_last > buttons_count:
                idx_last = buttons_count

            pages_count = int(buttons_count / max_page_buttons)
            choice_keys = list(choices.keys())[(idx_first if idx_first else choices_start_offset):idx_last]
            pagination_menu = [
                InlineKeyboardButton("<<", callback_data=BotMan.inlineKeyboardChoiceCallbackData(list_type, button_type, page=0)),
                InlineKeyboardButton(
                    "<",
                    callback_data=BotMan.inlineKeyboardChoiceCallbackData(list_type, button_type, page=page - 1 if page > 0 else 0),
                ),
                InlineKeyboardButton(
                    f"({page+1}/{pages_count+1})" if language != "fa" else persianify(f"({page+1}/{pages_count+1})"),
                    callback_data=jsonify(
                            {
                                "lt": list_type.value if list_type else None,
                                "bt": button_type.value,
                                "pg": page,
                                "v": f"$#{idx_first}:{idx_last}",
                            }
                        )
                ),
                InlineKeyboardButton(
                    ">",
                    callback_data=BotMan.inlineKeyboardChoiceCallbackData(list_type, button_type, page=page + 1 if page < pages_count else pages_count),
                ),
                InlineKeyboardButton(">>", callback_data=BotMan.inlineKeyboardChoiceCallbackData(list_type, button_type, page=pages_count)),
            ]
        else:
            choice_keys = choices.keys() if not choices_start_offset else list(choices.keys())[choices_start_offset:]

        row_length: int = 0
        row: List[InlineKeyboardButton] = []
        for choice in choice_keys:
            btn_text = choice if language != "fa" else choices[choice]
            row_length += 1 + int(len(btn_text) / 5)
            if choice in selected_ones:
                btn_text += "✅"
            row.append(InlineKeyboardButton(btn_text, callback_data=BotMan.inlineKeyboardChoiceCallbackData(list_type, button_type, choice, page)))
            if row_length >= 5:
                buttons.append(row)
                row = []
                row_length = 0
        if row:
            buttons.append(row)

        if pagination_menu:
            buttons.append(pagination_menu)

        if close_button:
            buttons.append(
                [
                    InlineKeyboardButton(
                        self.resourceman.keyboard("close", language),
                        callback_data=BotMan.inlineKeyboardChoiceCallbackData(list_type, button_type, page=-1),
                    )
                ]
            )
        return InlineKeyboardMarkup(buttons)

    def inline_url(
        self,
        urls_data: List[Dict[str, str]],
        language: str = "fa",
        columns_in_a_row: int = 2,
    ):
        """this function creates inline url keyboard for messages"""
        buttons_count = len(urls_data)
        full_rows_count = int(buttons_count / columns_in_a_row)
        buttons = [
            [
                InlineKeyboardButton(
                    self.resourceman.keyboard(urls_data[col + row * columns_in_a_row]["text_key"], language),
                    url=urls_data[col + row * columns_in_a_row]["url"],
                )
                for col in range(columns_in_a_row)
            ]
            for row in range(full_rows_count)
        ]
        full_rows_last_index = columns_in_a_row * full_rows_count
        if full_rows_last_index < buttons_count:
            buttons.append(
                [
                    InlineKeyboardButton(
                        self.resourceman.keyboard(urls_data[i]["text_key"], language),
                        url=urls_data[i]["url"],
                    )
                    for i in range(full_rows_last_index, buttons_count)
                ]
            )
        return InlineKeyboardMarkup(buttons)

    def action_inline_keyboard(
        self,
        action: QueryActions,
        data: Dict[str | int | None, str],
        language: str = "fa",
        columns_in_a_row: int = 2,
        in_main_keyboard: bool = False,
    ):
        """this function creates inline url keyboard for messages"""
        keys = list(data.keys())
        buttons_count = len(keys)
        full_rows_count = int(buttons_count / columns_in_a_row)
        buttons = [
            [
                InlineKeyboardButton(
                    text=self.resourceman.keyboard(data[keys[col + row * columns_in_a_row]], language) if not in_main_keyboard
                        else self.resourceman.mainkeyboard(data[keys[col + row * columns_in_a_row]], language),
                    callback_data=self.actionCallbackData(action, keys[col + row * columns_in_a_row]),
                )
                for col in range(columns_in_a_row)
            ]
            for row in range(full_rows_count)
        ]

        full_rows_last_index = columns_in_a_row * full_rows_count
        if full_rows_last_index < buttons_count:
            buttons.append(
                [
                    InlineKeyboardButton(
                        self.resourceman.keyboard(data[keys[i]], language),
                        callback_data=self.actionCallbackData(action, keys[i]),
                    )
                    for i in range(full_rows_last_index, buttons_count)
                ]
            )
        return InlineKeyboardMarkup(buttons)

    def users_list_menu(
        self,
        users: List[Account],
        list_type: QueryActions,
        columns_in_a_row: int = 3,
        page: int = 0,
        max_page_buttons: int = 90,
        language: str = "fa",
    ):
        """this function creates inline keyboard for users data as callback data"""
        buttons_count = len(users)

        pagination_menu: List[InlineKeyboardButton] | None = None
        pagination_callback_data = lambda page: BotMan.actionCallbackData(list_type, None, page)

        if buttons_count > max_page_buttons:
            idx_first, idx_last = page * max_page_buttons, (page + 1) * max_page_buttons
            if idx_last > buttons_count:
                idx_last = buttons_count
            lbl_first, lbl_last = (persianify(idx_first + 1), persianify(idx_last)) if language == "fa" else (idx_first + 1, idx_last)

            pages_count = int(buttons_count / max_page_buttons)
            users = list(users)[idx_first:idx_last]
            pagination_menu = [
                InlineKeyboardButton("<<", callback_data=pagination_callback_data(0)),
                InlineKeyboardButton(
                    "<",
                    callback_data=pagination_callback_data(page=page - 1 if page > 0 else 0),
                ),
                InlineKeyboardButton(
                    f"({lbl_first}-{lbl_last})",
                    callback_data=pagination_callback_data(page),
                ),
                InlineKeyboardButton(
                    ">",
                    callback_data=pagination_callback_data(page=page + 1 if page < pages_count else int(pages_count)),
                ),
                InlineKeyboardButton(">>", callback_data=pagination_callback_data(pages_count)),
            ]

            buttons_count = len(users)

        full_rows_count = int(buttons_count / columns_in_a_row)

        buttons = [
            [
                InlineKeyboardButton(
                    text=str(users[col + row * columns_in_a_row]),
                    callback_data=self.actionCallbackData(list_type, users[col + row * columns_in_a_row].chat_id),
                )
                for col in range(columns_in_a_row)
            ]
            for row in range(full_rows_count)
        ]

        full_rows_last_index = columns_in_a_row * full_rows_count
        if full_rows_last_index < buttons_count:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=str(users[i]),
                        callback_data=self.actionCallbackData(list_type, users[i].chat_id),
                    )
                    for i in range(full_rows_last_index, buttons_count)
                ]
            )
        if pagination_menu:
            buttons.append(pagination_menu)

        buttons.append(
            [
                InlineKeyboardButton(
                    self.resourceman.keyboard("close"),
                    callback_data=pagination_callback_data(-1),
                )
            ]
        )
        return InlineKeyboardMarkup(buttons)

    async def handle_users_menu_page_change(self, operator: Account, query: CallbackQuery,
                                            callback_data: Dict[str, str | int | None],
                                            source_func: Callable[...,List[Account]], action: QueryActions):
        try:
            if callback_data["pg"] is None or (page := int(callback_data["pg"])) == -1:
                operator.change_state()
                await asyncio.gather(
                    query.message.reply_text(
                        text=self.text("what_can_i_do", operator.language),
                        reply_markup=self.mainkeyboard(operator),
                    ),
                    query.message.edit_text(self.text("list_updated", operator.language)),
                    return_exceptions=True,
                )
                return True
            menu = self.users_list_menu(
                source_func(),
                action,
                columns_in_a_row=3,
                page=page,
                language=operator.language,
            )
            await query.message.edit_reply_markup(reply_markup=menu)
        except:
            return False # Indicator of sth went wrong
        return True

    def keyboard_from(self, language: str, *row_keys: str):
        buttons = []
        for key in row_keys:
            buttons.append([self.resourceman.keyboard(key, language)])
        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    async def has_subscribed_us(self, chat_id: int, context: CallbackContext) -> bool:
        try:
            chat1, chat2 = await asyncio.gather(
                context.bot.get_chat_member(self.channels[0]["id"], chat_id), context.bot.get_chat_member(self.channels[-1]["id"], chat_id)
            )
        except BadRequest as ex:
            log(
                "Can not determine channel membership, seems the bot is not an admin in specified channels.",
                ex,
            )
            await self.inform_admins("bot_not_channel_admin", context, is_error=True)
            return False
        return chat1.status != ChatMember.LEFT and chat2.status != ChatMember.LEFT

    async def inform_admins(self, message_key: str, context: CallbackContext, is_error: bool = False):
        message_text = self.error if is_error else self.text
        tasks = []
        for admin in Account.getGodUsers(just_hardcode_admin=False):
            try:
                tasks.append(
                    context.bot.send_message(
                        chat_id=admin.chat_id,
                        text=message_text(message_key, admin.language),
                    )
                )
            except:
                pass
        await asyncio.gather(*tasks, return_exceptions=True)

    async def ask_for_subscription(self, update: Update, language: str = "fa"):
        await update.message.reply_text(
            self.resourceman.text("ask_subscription_message", language) % (self.channels[0]["username"], self.channels[-1]["username"]),
            reply_markup=self.action_inline_keyboard(self.QueryActions.IVE_SUBSCRIBED, {True: "ive_subscribed"}),
        )
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

    async def next_post(self, language: str = "fa"):
        return await self.postman.create_post(post_interval=self.main_plan_interval, language=language)

    def check_price_alarms(self) -> List[PriceAlarm]:
        """Checks all user alarms and finds alarms that has gone off"""
        alarms = PriceAlarm.get()
        # TODO: Define a pre_latest_data, check for currencies that have changed in 10m and then get alarms by currencies
        triggered_alarms = []
        for alarm in alarms:
            try:
                if alarm.market == MarketOptions.CRYPTO:
                    alarm.current_price = self.crypto_serv.get_single_price(alarm.token, alarm.target_unit)
                    alarm.full_token_name = {
                        "en": alarm.token.upper(),
                        "fa": self.crypto_serv.getPersianName(alarm.token.upper()),
                    }
                else:
                    alarm.current_price = self.currency_serv.get_single_price(alarm.token, alarm.target_unit)
                    alarm.full_token_name = {
                        "en": alarm.token.upper(),
                        "fa": self.currency_serv.getPersianName(alarm.token.upper()),
                    }

                if alarm.current_price is not None:
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
            except Exception as x:
                log(
                    f"Failed examining Alarm state: id={alarm.id} account={alarm.chat_id}: {alarm}",
                    x,
                    category_name="ALARM",
                )
        return triggered_alarms

    async def handle_possible_alarms(self, send_message_func):
        # start notifying users [if at least one alarm went off]
        unit_names = {
            "irt": {"fa": self.currency_serv.getPersianName("IRT"), "en": "IRT"},
            "usd": {"fa": self.currency_serv.getPersianName("USD"), "en": "USD"},
        }  # shortcut variable to prevent getting it in every step of the loop
        for alarm in self.check_price_alarms():
            try:
                account = Account.getById(alarm.chat_id, no_fastmem=True)
                target_price = cut_and_separate(alarm.target_price)
                current_price = cut_and_separate(alarm.current_price)
                currency_name, unit_name = (
                    alarm.full_token_name[account.language],
                    unit_names[alarm.target_unit][account.language],
                )

                if account.language == "fa":
                    target_price, current_price = persianify(target_price), persianify(current_price)
                price_alarm_text = (
                    self.text("price_alarm", account.language)
                    % (
                        currency_name,
                        target_price,
                        unit_name,
                    )
                    + "\n\n"
                    + self.text("current_price_is", account.language)
                    % (
                        currency_name,
                        current_price,
                        unit_name,
                    )
                )
                await send_message_func(chat_id=account.chat_id, text=price_alarm_text)
                alarm.disable()
            except Exception as ex:
                log("Failed notifying user of triggered alarm:", ex, category_name="ALARM")

    async def show_reached_max_error(self, telegram_handle: Update | CallbackQuery, account: Account, max_value: int):
        if not account.is_premium:
            await self.send_message_with_premium_button(
                telegram_handle,
                text=self.error("max_selection", account.language) % (max_value,) + self.error("get_premium", account.language),
            )
        else:
            await telegram_handle.message.reply_text(text=self.error("max_selection", account.language) % (max_value,))

    async def send_message_with_premium_button(self, update: Update | CallbackQuery, text: str):
        link = f"https://t.me/{Account.getHardcodeAdmin()['username']}"
        await update.message.reply_text(
            text=text,
            reply_markup=self.inline_url([{"text_key": "premium", "url": link}]),
        )

    async def show_settings_menu(self, update: Update):
        account = Account.get(update.message.chat)
        keyboard = ReplyKeyboardMarkup(
            (
                [
                    [KeyboardButton(BotMan.Commands.TUTORIALS_FA.value)],
                    [
                        KeyboardButton(BotMan.Commands.FACTORY_RESET_FA.value),
                        KeyboardButton(BotMan.Commands.SET_BOT_LANGUAGE_FA.value),
                    ],
                    [
                        KeyboardButton(BotMan.Commands.OUR_OTHERS_FA.value),
                        KeyboardButton(BotMan.Commands.SUPPORT_FA.value),
                    ],
                    [KeyboardButton(BotMan.Commands.RETURN_FA.value)],
                ]
                if account.language != "en"
                else [
                    [KeyboardButton(BotMan.Commands.TUTORIALS_EN.value)],
                    [
                        KeyboardButton(BotMan.Commands.FACTORY_RESET_EN.value),
                        KeyboardButton(BotMan.Commands.SET_BOT_LANGUAGE_EN.value),
                    ],
                    [
                        KeyboardButton(BotMan.Commands.OUR_OTHERS_EN.value),
                        KeyboardButton(BotMan.Commands.SUPPORT_EN.value),
                    ],
                    [KeyboardButton(BotMan.Commands.RETURN_EN.value)],
                ]
            ),
            resize_keyboard=True,
            one_time_keyboard=False,
        )
        return await update.message.reply_text(
            self.resourceman.mainkeyboard("settings", account.language),
            reply_markup=keyboard,
        )

    async def clear_unwanted_menu_messages(self, update: Update, context: CallbackContext, operation_result):
        if isinstance(operation_result, Message):
            await asyncio.gather(
                context.bot.delete_message(chat_id=update.message.chat_id, message_id=operation_result.message_id),
                update.message.delete(),
                return_exceptions=True,
            )
            return
        await update.message.delete()

    async def list_premiums(self, update: Update | CallbackQuery, list_type: QueryActions, only_menu: bool = False) -> InlineKeyboardMarkup | None:
        try:
            account = Account.get(update.message.chat)
            premiums = Account.getPremiumUsers()
            if not premiums:
                if only_menu:
                    return None
                await update.message.reply_text(
                    text=self.text("no_premium_users_found", account.language),
                    reply_markup=self.mainkeyboard(account),
                )
                return None
            menu = self.users_list_menu(premiums, list_type, columns_in_a_row=3, page=0, language=account.language)
            if only_menu:
                return menu
            await update.message.reply_text(text=self.text("select_user", account.language), reply_markup=menu)
        except Exception as x:
            log("Problem while listing premium users:", x, "Admin")

    @staticmethod
    def identifyUser(update: Update) -> Account | None:
        """Get the user's Account object from update object by one of these methods:
            1- providing a forwarded message from the desired user
            2- providing the username of the user
            3- providing the chat_id of the user.
        """
        if update.message.forward_from:
            target_chat_id = update.message.forward_from.id
            user = Account.getById(target_chat_id)
            user.name = update.message.forward_from
            user.firstname = update.message.forward_from.first_name
            return user

        if update.message.text[0] == "@":
            if user := Account.getByUsername(update.message.text):
                return user
            return None

        try:
            target_chat_id = int(update.message.text)
            return Account.getById(target_chat_id)
        except:
            pass
        return None

    @staticmethod
    def stringToNumber(num: str) -> int | float:
        thousands = 1
        if num[0].isdigit() and not num[-1].isdigit():
            thousands, num = extract_thousands(num)
        f = float(num) * thousands
        intf = int(f)
        return f if intf != f else intf

    @staticmethod
    def extractMultiplier(word: str):
        try:
            return BotMan.stringToNumber(word)
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
            prev_word: str | float = words[i - 1] if i else 1.0
            slug, word_count = finder.search_around(self.crypto_serv.coinsInPersian, i)
            if slug:
                multiplier = BotMan.extractMultiplier(prev_word)
                crypto_amounts.add(f"{multiplier} {slug}")
            else:
                slug, word_count = finder.search_around(self.currency_serv.currenciesInPersian, i)

                if not slug:
                    slug, word_count = finder.search_around(self.currency_serv.persianShortcuts, i)
                if slug:
                    multiplier = BotMan.extractMultiplier(prev_word)
                    currency_amounts.add(f"{multiplier} {slug}")
            i += word_count
        return crypto_amounts, currency_amounts

    def construct_post(
        self,
        res_fiat: str,
        res_gold: str,
        res_crypto: str,
        language: str = "fa",
        use_tags: bool = True,
    ):
        if not use_tags:
            res = filter(lambda x: x, [res_fiat, res_gold, res_crypto])
            return "\n".join(res)
        tags_fiat = self.text("markets_fiat", language)
        tags_gold = self.text("markets_gold", language)
        tags_crypto = self.text("markets_crypto", language)

        res = filter(
            lambda x: x[1],
            [(tags_fiat, res_fiat), (tags_gold, res_gold), (tags_crypto, res_crypto)],
        )
        return "\n".join([f"{tag}\n{text}" for (tag, text) in res])

    def create_crypto_equalize_message(
        self,
        unit: str,
        amount: float | int,
        target_cryptos: List[str] | None,
        target_currencies: List[str] | None,
        language: str = "fa",
        use_tags: bool = True,
    ):
        res_crypto, _, absolute_irt = self.crypto_serv.equalize(unit, amount, target_cryptos, (language := language))
        res_fiat, res_gold = (
            self.currency_serv.irt_to_currencies(absolute_irt, unit, target_currencies, language) if target_currencies else (None, None)
        )
        post = self.construct_post(res_fiat, res_gold, res_crypto, language, use_tags)
        if not post:
            return self.text("no_token_selected")
        amount = normal_float_display(amount)
        header = self.text("equalize_header", language) % (
            amount if language != "fa" else persianify(amount),
            unit if language != "fa" else self.crypto_serv.coinsInPersian[unit],
        )
        return f"{header}\n\n{post}"

    def create_currency_equalize_message(
        self,
        unit: str,
        amount: float | int,
        target_cryptos: List[str] | None,
        target_currencies: List[str] | None,
        language: str = "fa",
        use_tags: bool = True,
    ):
        res_fiat, res_gold, absolute_usd, _ = self.currency_serv.equalize(unit, amount, target_currencies, (language := language))
        res_crypto = self.crypto_serv.usd_to_cryptos(absolute_usd, unit, target_cryptos, language) if target_cryptos else None
        post = self.construct_post(res_fiat, res_gold, res_crypto, language, use_tags)
        if not post:
            return self.text("no_token_selected")
        amount = normal_float_display(amount)
        header = self.text("equalize_header", language) % (
            amount if language != "fa" else persianify(amount),
            (self.currency_serv.getEnglishTitle(unit) if language != "fa" else self.currency_serv.currenciesInPersian[unit]),
        )
        return f"{header}\n\n{post}"

    async def prepare_channel(self, ctx: CallbackContext, owner: Account, channel_id: int, interval: int):
        try:
            channel_response = await ctx.bot.send_message(chat_id=channel_id, text="OK")

            channel = Channel(
                channel_id,
                owner.chat_id,
                int(interval),
                channel_response.chat.username or None,
                channel_response.chat.title or "Unnamed",
                language=owner.language,
            )
            channel.create()

            post_interval, desc_en, desc_fa = PostInterval(minutes=interval).timestamps
            interval_description: str = None
            if owner.language == "fa":
                post_interval = persianify(post_interval)
                interval_description = persianify(desc_fa)
            else:
                interval_description = desc_en
            await asyncio.gather(
                ctx.bot.delete_message(chat_id=channel_id, message_id=channel_response.message_id),
                ctx.bot.send_message(
                    chat_id=owner.chat_id,
                    text=self.text("click_to_start_channel_posting", owner.language) % (post_interval, interval_description),
                    reply_markup=self.action_inline_keyboard(
                        self.QueryActions.START_CHANNEL_POSTING,
                        {channel_id: "start"},
                        owner.language,
                        columns_in_a_row=1,
                    ),
                ),
                return_exceptions=True,
            )
        except MaxAddedCommunityException:
            await ctx.bot.send_message(
                chat_id=owner.chat_id,
                text=self.error("max_channels_reached", owner.language),
            )
            return False
        except Exception as ex:
            log(
                "Getting and planning channel data failed.",
                ex,
                category_name="Channels",
            )
            return False
        return True

    async def use_input_channel_chat_info(
        self,
        update: Update,
        context: CallbackContext,
        account: Account,
        channel_chat: Chat,
        next_state: Account.States = Account.States.SELECT_POST_INTERVAL,
    ):
        community_type = account.get_cache("community")
        if (community_type := BotMan.CommunityType.which(community_type)) == BotMan.CommunityType.CHANNEL and (
            old_channel := Channel.getByOwner(account.chat_id)
        ):
            try:
                old_channel_id = old_channel.id
                old_channel.change(channel_chat)
                await asyncio.gather(
                    context.bot.leave_chat(chat_id=old_channel_id),
                    update.message.reply_text(
                        self.text("update_successful", account.language),
                        reply_markup=self.get_community_config_keyboard(BotMan.CommunityType.CHANNEL, account.language),
                    ),
                    return_exceptions=True,
                )
                account.change_state(
                    cache_key="community",
                    data=BotMan.CommunityType.CHANNEL.value,
                )
            except Exception as x:
                log("sth went wrong while changing channel:", x, "Channel")
            return
        await update.message.reply_text(self.text('channel_recognition_done', account.language),
                                  reply_markup=self.mainkeyboard(account))
        await self.prepare_set_interval_interface(update, account, channel_chat.id, next_state)

    async def prepare_set_interval_interface(
        self,
        update: Update,
        account: Account,
        channel_chat_id: int,
        next_state: Account.States,
    ):
        account.change_state(next_state, "channel_chat_id", channel_chat_id)
        response_message = await update.message.reply_text(
            self.text("select_post_interval", account.language),
            reply_markup=self.arrangeInlineKeyboardButtons(Channel.SupportedIntervals, self.QueryActions.SELECT_POST_INTERVAL),
        )
        account.add_cache("interval_menu_msg_id", response_message.message_id)

    async def handle_set_interval_outcome(self, update: Update | CallbackQuery, context: CallbackContext, interval: int):
        account = Account.get(update.message.chat)
        channel_id = account.get_cache("channel_chat_id")
        try:
            if account.state == Account.States.SELECT_POST_INTERVAL:
                if not channel_id or not (await self.prepare_channel(context, account, channel_id, interval)):
                    raise InvalidInputException("Invalid channel data.")
            elif account.state == Account.States.CHANGE_POST_INTERVAL:
                channel = Channel.get(channel_id)
                if not channel:
                    raise NoSuchThingException(channel_id)
                channel.interval = interval
                channel.last_post_time = None
                channel.save()
                await update.message.reply_text(self.text("update_successful", account.language))
            else:
                raise InvalidInputException("Invalid account state.")
            return True
        except NoSuchThingException:
            await update.message.reply_text(
                self.error("no_channels", account.language),
                reply_markup=self.mainkeyboard(account),
            )
        except InvalidInputException:
            await update.message.reply_text(
                self.error("error_while_planning_channel", account.language),
                reply_markup=self.mainkeyboard(account),
            )
        return False

    @staticmethod
    def arrangeInlineKeyboardButtons(
        list_of_keys: list[GroupInlineKeyboardButtonTemplate],
        query_action: QueryActions,
    ):
        keys_count = len(list_of_keys)
        keys = [
            [
                InlineKeyboardButton(
                    list_of_keys[j].title,
                    callback_data=BotMan.actionCallbackData(query_action, list_of_keys[j].value),
                )
                for j in range(i * 5, (i + 1) * 5 if (i + 1) * 5 < keys_count else keys_count)
            ]
            for i in range(math_ceil(keys_count // 5))
        ]

        return InlineKeyboardMarkup(keys)

    @staticmethod
    def handleMarketSelection(
        account: Account,
        list_type: SelectionListTypes,
        market: MarketOptions,
        symbol: str | None = None,
    ):
        target_set: List[str]
        related_set: List[str]
        save_func: callable = account.save

        match list_type:
            case SelectionListTypes.CALCULATOR:
                (target_set, related_set) = (
                    (account.calc_cryptos, account.calc_currencies)
                    if market == MarketOptions.CRYPTO
                    else (account.calc_currencies, account.calc_cryptos)
                )
            case SelectionListTypes.USER_TOKENS:
                (target_set, related_set) = (
                    (account.desired_cryptos, account.desired_currencies)
                    if market == MarketOptions.CRYPTO
                    else (account.desired_currencies, account.desired_cryptos)
                )
            case SelectionListTypes.GROUP_TOKENS:
                my_group = Group.getByOwner(account.chat_id)
                if not my_group:
                    raise NoSuchThingException(account.chat_id, "Group")
                (target_set, related_set) = (
                    (my_group.selected_coins, my_group.selected_currencies)
                    if market == MarketOptions.CRYPTO
                    else (my_group.selected_currencies, my_group.selected_coins)
                )
                save_func = my_group.save
            case SelectionListTypes.CHANNEL_TOKENS:
                my_channel = Channel.getByOwner(account.chat_id)
                if not my_channel:
                    raise NoSuchThingException(account.chat_id, "Channel")
                (target_set, related_set) = (
                    (my_channel.selected_coins, my_channel.selected_currencies)
                    if market == MarketOptions.CRYPTO
                    else (my_channel.selected_currencies, my_channel.selected_coins)
                )
                save_func = my_channel.save
            case SelectionListTypes.ALARM | SelectionListTypes.EQUALIZER_UNIT:
                return None
            case _:
                raise ValueError(f"Invalid list type selected by: {list_type.value}")

        if symbol:
            if symbol.upper() not in target_set:
                if len(target_set) + len(related_set) >= account.allowed_tokens_count:
                    raise ValueError(account.allowed_tokens_count)

                target_set.append(symbol)
            else:
                target_set.remove(symbol)
            save_func()
        return target_set

    @staticmethod
    def factoryResetAccount(account: Account):
        account.factory_reset()

        # disable(delete) all alarms
        user_alarms = PriceAlarm.getUserAlarms(account.chat_id)
        if user_alarms:
            for alarm in user_alarms:
                alarm.disable()

        # stop(delete) all planned channels
        Channel.deleteAllUserChannels(account.chat_id)

        Group.deleteAllUserGroups(account.chat_id)

    @staticmethod
    def getCommunity(community_type: int | CommunityType, owner_id: int) -> Group | Channel | None:
        if not community_type or (isinstance(community_type, BotMan.CommunityType) and not community_type.value):
            return None
        return BotMan.CommunityType.toClass(
            community_type if not isinstance(community_type, BotMan.CommunityType) else community_type.value
        ).getByOwner(owner_id)

    async def handle_channel_posting(self, channel: Channel, context: CallbackContext, update_last_post_time_targets: List[int]):
        owner = Account.getById(channel.owner_id, no_fastmem=True)  # TODO: Implement SQL-JOIN for fast owner loading.
        if not owner.is_premium:
            return  # TODO: Maybe Deactivate the channel? or inform users of their premium plan ending?
        try:
            post = self.postman.create_channel_post(channel)
            await context.bot.send_message(chat_id=channel.id, text=post)
            update_last_post_time_targets.append(channel.id)
        except Forbidden:
            await context.bot.send_message(chat_id=owner.chat_id,
                                           text=self.error('bot_was_kicked_from_your_channel', owner.language))
        except Exception as x:
            log(
                f"Failed sending post to channel: {channel.id}, title:{channel.title}, at its due.",
                x,
                category_name="Channels",
            )

    async def process_channels(self, context: CallbackContext):
        """loop through channels and send post in ones that their interval due has reached."""
        channels = Channel.actives()
        now = now_in_minute()

        update_last_post_time_targets = []
        post_tasks: list[Coroutine[Any, Any, None]]  = []
        for channel in channels:
            if not channel.last_post_time or (now - channel.last_post_time >= channel.interval):
                post_tasks.append(self.handle_channel_posting(channel, context, update_last_post_time_targets))
        await asyncio.gather(*post_tasks)
        if update_last_post_time_targets:
            Channel.updateLastPostTimes(update_last_post_time_targets)

    async def downgrade_user(self, user: Account, context: CallbackContext | None = None):
        user.downgrade()
        if context:
            await context.bot.send_message(chat_id=user.chat_id, text=self.text("plan_expired", user.language))
        Channel.deactivateUserChannels(user.chat_id)

    async def do_hourly_check(self, context: CallbackContext):
        """Garbage collect fast mems, remove messages supposed to be removed, etc."""
        Account.garbageCollect()
        Group.garbageCollect()

        if not self.last_daily_check or now_in_minute() - self.last_daily_check >= 1440:
            await self.do_daily_checks(context)
            log("Daily checks has been performed successfully.", category_name='Schedules')

    async def do_daily_checks(self, context: CallbackContext):
        today = tz_today().date()
        async_tasks: List[Coroutine[Any, Any, bool | Message]] = []

        possible_premiums = Account.getPremiumUsers(even_possibles=True)
        for user in possible_premiums:
            try:
                user_premium_end_date = user.premium_date
                if user_premium_end_date < today:
                    await self.downgrade_user(user, context)
                else:
                    days_remaining = (today - user_premium_end_date).days
                    if days_remaining in (7, 3, 1):
                        days_remaining = str(days_remaining) if user.language != "fa" else persianify(days_remaining)
                        async_tasks.append(
                            context.bot.send_message(
                                chat_id=user.chat_id,
                                text=self.text("premium_expiry_is_close", user.language) % (days_remaining,),
                            )
                        )
            except Exception as x:
                log("User daily checkout failed", x, category_name="Checkouts")

        db = Account.database()
        now = now_in_minute()
        deleting_messages = db.get_messages_passed_their_due()

        if deleting_messages:
            for i, msg in enumerate(deleting_messages):
                try:
                    (_, chat_id, msg_id) = msg
                    if chat_id and msg_id:
                        async_tasks.append(
                            context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        )
                except:
                    pass
            db.throw_away_messages_passed_time(from_time=now)

        await asyncio.gather(*async_tasks)

    @staticmethod
    def refreshMemory():
        Account.fastMemInstances.clear()
        Group.fastMemInstances.clear()
        BotSettings.refresh()  # this one calls gc.collect too

    @staticmethod
    def createReportByLabels(
        stats: Dict[str, int],
        all_labels: Dict[str, Dict[str, Dict[str, str]]],
        desired_labels: tuple,
        word_unknown: str,
        language: str = "fa",
    ):
        language = language.lower()
        report = all_labels["title"][language] + "\n\n"
        for part in desired_labels:
            labels = all_labels[part]
            for label in labels:
                text = labels[label]
                current: str | None = None
                try:
                    current = text[language]
                    report += f"{current}: {stats[label]}\n"
                except Exception:
                    if current:
                        report += f"{current}: {word_unknown}"
            report += "\n"
        return report

    @staticmethod
    def collectBotStats(language: str = "fa"):
        db = Account.database()
        account_stats = db.get_user_stats()
        channels_count = db.get_active_channels_count()
        groups_count = db.get_all_groups_count()
        admin_json = load_json("admin", "resources")
        all_labels = admin_json["statistics"]
        word_unknown: str | None
        try:
            word_unknown = all_labels["unknown"][language]
        except:
            word_unknown = "Unknown"
        total_report = BotMan.createReportByLabels(
            account_stats,
            all_labels,
            ("joins", "premiums", "total"),
            word_unknown,
            language,
        )
        language = language.lower()
        try:
            total_report += f"{all_labels['channels'][language]}: {channels_count if channels_count is not None else word_unknown}\n"
        except Exception as x:
            total_report += f"{all_labels['channels'][language]}: {word_unknown}\n"
        try:
            total_report += f"{all_labels['groups'][language]}: {groups_count if groups_count is not None else word_unknown}\n"
        except Exception as x:
            total_report += f"{all_labels['groups'][language]}: {word_unknown}\n"
        interaction_report = BotMan.createReportByLabels(
            account_stats,
            all_labels["interactions"],
            ("premiums", "free"),
            word_unknown,
            language,
        )
        return total_report, interaction_report

    def get_token_state(self, market: MarketOptions, token: str, price_unit: str):
        current_price: float
        currency_name: str
        match market:
            case MarketOptions.CRYPTO:
                current_price = self.crypto_serv.get_single_price(token, price_unit)
                currency_name = self.crypto_serv.coinsInPersian[token]
            case MarketOptions.GOLD | MarketOptions.CURRENCY:
                current_price = self.currency_serv.get_single_price(token, price_unit)
                currency_name = self.currency_serv.currenciesInPersian[token]
            case _:
                if token in self.crypto_serv.coinsInPersian:
                    current_price = self.crypto_serv.get_single_price(token, price_unit)
                    currency_name = self.crypto_serv.coinsInPersian[token]
                elif token in self.currency_serv.currenciesInPersian:
                    current_price = self.currency_serv.get_single_price(token, price_unit)
                    currency_name = self.currency_serv.currenciesInPersian[token]
                else:
                    raise ValueError("Unknown token and market")
        return currency_name, current_price

    @staticmethod
    async def deleteRedundantMessage(account: Account, context: CallbackContext, delete_cache: bool = True):
        try:
            msg_to_delete = account.get_cache("msg2delete")
            if msg_to_delete:
                await context.bot.delete_message(chat_id=account.chat_id, message_id=int(msg_to_delete))
                if delete_cache:
                    account.delete_specific_cache("msg2delete")
        except Exception as x:
            log("Failed to remove redundant message:", x, category_name="Minors")

    @staticmethod
    def getLongText(key: str, language: str = "fa"):
        import resources.longtext as long_texts

        return long_texts.TUTORIALS_TEXT[key][language.lower()]

    @staticmethod
    def updateUserLanguage(account: Account, language: str):
        Channel.updateUserChannels(account)
        account.language = language
        account.save()
