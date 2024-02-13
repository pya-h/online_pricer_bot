from db.vip_models import VIPAccount
import requests, json
from tools.manuwriter import log
from enum import Enum
from math import ceil
from webhook.p4ya_telegraph_basics import CanBeKeyboardItemInterface
from db.vip_models import UserStates
from typing import Callable, Dict, List, Union

class ChatTypes(Enum):
    USER = "user"
    CHANNEL = "channel"
    GROUP = "group"
    NONE = "none"

    @staticmethod
    def corresponding_member(value: str):
        value = value.lower()
        for member in ChatTypes:
            if member.value == value:
                return member

        return ChatTypes.NONE


class ForwardOrigin:
    def __init__(self, forward_data: dict) -> None:
        self.type: ChatTypes = ChatTypes.corresponding_member(forward_data['type'])
        self.id: int = None
        self.message_id: int = None
        self.title: str = None
        self.username: str = None
        if self.type == ChatTypes.CHANNEL:
            self.id = forward_data['chat']['id']
            self.message_id = forward_data['message_id']
            self.title = forward_data['chat']['title']
            if 'username' in forward_data['chat']:
                self.username = forward_data['chat']['username']
        elif self.type == ChatTypes.USER:
            self.id = forward_data['sender_user']['id']
            self.title = forward_data['sender_user']['first_name']
            if 'username' in forward_data['sender_user']:
                self.username = forward_data['sender_user']['username']

    def __str__(self) -> str:
        return f"type: {self.type}\ntitle:{self.title}\nid:{self.id}\nusername:{self.username}"


class Keyboard:
    def __init__(self, *rows: list) -> None:
        self.keys = list(rows)
        self.one_time_keyboard = False
        self.resize_keyboard = True

    def make_one_time(self):
        self.one_time_keyboard = True

    def prevent_resizing(self):
        self.resize_keyboard = False

    def as_dict(self) -> dict:
        return {
            "keyboard": self.keys,
            "one_time_keyboard": self.one_time_keyboard,
            "resize_keyboard": self.resize_keyboard
        }

    def as_json(self) -> str:
        '''Return the json that canbe used for passing to reponse payload'''
        return json.dumps(self.as_dict())

    def attach_to(self, response_payload: dict) -> None:
        '''Attach the keyboard to the response payload, to make it easy for adding keyboard to messages'''
        response_payload['reply_markup'] = self.as_json()  # dicts are passed by reference, so there is no need to return this



class InlineKey:
    '''Inline kyeboard items'''
    def __init__(self, text: str, callback_data: dict|str = None, url: str = None, ask_location: bool = False, ask_contact: bool = False) -> None:
        self.text: str = text
        # From the fields below only one must be passed, otherwise it will consider it first as callback_data, then url, then ...
        self.callback_data: dict|str = callback_data
        self.url: str = url
        self.request_location: bool = ask_location
        self.request_contact: bool = ask_contact

    def set_params(self, param: dict):
        if "callback_data" in param:
            self.callback_data = param["callback_data"]
        elif "url" in param:
            self.url = param["url"]
        elif "request_contact" in param:
            self.request_contact = param["request_contact"]
        elif "request_location" in param:
            self.request_location = param["request_location"]
        return self


    def as_dict(self) -> dict:
        value = {"text": self.text}
        if self.callback_data:
            value["callback_data"] = json.dumps(self.callback_data) if isinstance(self.callback_data, dict) else str(self.callback_data)
        elif self.url:
            value["url"] = self.url
        elif self.request_contact:
            value["request_contact"] = True
        elif self.request_location:
            value["request_location"] = True
        else:
            value["callback_data"] = "null"

        return value


class InlineKeyboard(Keyboard):
    '''Telegram Inline keyboard implementation, to make it easy for adding inline keyboards to your messages'''
    def __init__(self, *rows):
        self.keys = list(rows)

    def make_standard_key(self, key: any) -> InlineKey:
        v = None
        try:
            v = key if isinstance(key, InlineKey) \
                else InlineKey(text=key["text"]).set_params(key) if isinstance(key, dict) \
                else InlineKey(str(key))
        except:
            v = InlineKey(text="!!")
        return v

    def as_dict(self) -> dict:
        '''Convert the obbject to a dict so then it be converted to a propper json. It's written in a way that it considers any kind of key param type'''
        if not len(self.keys):
            return None

        arranged_keys = [
            [self.make_standard_key(col).as_dict() for col in (row if isinstance(row, list) else [row])] \
                for row in self.keys]

        return {
            "inline_keyboard": arranged_keys
        }

    @staticmethod
    def Arrange(list_of_keys: list[CanBeKeyboardItemInterface], callback_action: str):
        keys_count = len(list_of_keys)
        keys = [[ InlineKey(list_of_keys[j].title(), {"a": callback_action, "v": list_of_keys[j].value()}) \
                 for j in range(i * 5, (i + 1) * 5 if (i + 1) * 5 < keys_count else keys_count)] \
                    for i in range(ceil(keys_count // 5))]

        return InlineKeyboard(*keys)


class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg: dict = data['message']
        self.id: int = self.msg['message_id'] if 'message_id' in self.msg else None
        self.text: str =  self.msg['text']

        self.by: VIPAccount = VIPAccount.Get(self.msg['chat']['id'])
        self.chat_id: int = self.msg['chat']['id']
        self.forward_origin: ForwardOrigin = ForwardOrigin(self.msg['forward_origin']) if 'forward_origin' in self.msg else None

    @staticmethod
    def Text(target_chat_id: str, text: str = ''):
        return TelegramMessage({"message": {
            "text": text,
            "chat": {
                "id": target_chat_id
            }
        }})


class TelegramCallbackQuery(TelegramMessage):

    def __init__(self, data: dict) -> None:
        super().__init__(data['callback_query'])
        self.data = data['data']
        self.action: str = self.data['a'] if 'a' in self.data else None
        self.value: str = self.data['v'] if 'v' in self.data else None


class TelegramBotCore:
    ''' Main and static part of the class '''
    def __init__(self, token: str, username: str, host_url: str, text_resources: dict, _main_keyboard: Dict[str, Keyboard]|Keyboard = None) -> None:
        self.token = token
        self.bot_api_url = f"https://api.telegram.org/bot{self.token}"
        self.host_url = host_url
        self.username = username
        self.text_resources: dict = text_resources  # this is for making add multi-language support to the bot
        self.middleware_handlers: list[dict] = []
        self.state_handlers: Dict[UserStates, Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]]] = dict()
        self.command_handlers: Dict[str, Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]]] = dict()
        self.message_handlers: Dict[str, Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]]] = dict()  # bot handlers, fills with add_handler
        self.callback_query_hanndlers: Dict[str, Callable[[TelegramBotCore, TelegramCallbackQuery], Union[TelegramMessage, Keyboard|InlineKeyboard]]] = dict()
        # these handler will be checked when running bot.handle
        self._main_keyboard: Dict[str, Keyboard]|Keyboard = _main_keyboard


    def main_keyboard(self, user_language: str = None) -> Keyboard:
        if isinstance(self._main_keyboard, Keyboard):
            return self._main_keyboard
        if isinstance(self, dict):
            if not user_language or user_language not in self._main_keyboard:
                return self._main_keyboard.values()[0]
            return self._main_keyboard[user_language]
        return None

    def send(self, message: TelegramMessage, keyboard: Keyboard|InlineKeyboard = None):
        url = f"{self.bot_api_url}/sendMessage"
        chat_id = message.chat_id # message.by.chat_id
        payload = {'chat_id': chat_id, 'text': message.text}
        if keyboard:
            keyboard.attach_to(payload)
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log(f"User-Responding Failure => status code:{response.status_code}\n\tChatId:{message.by.chat_id}\nResponse text: {response.text}", category_name="VIP_FATAL")
        return response  # as dict

    def get_telegram_link(self) -> str:
        return f'https://t.me/{self.username}'

    def text(self, text_key: str, language: str = 'fa') -> str:  # short for gettext
        try:
            return self.text_resources[text_key][language]
        except:
            pass
        return "پاسخ نامعلوم" if language == 'fa' else "Unknown response"

    def keyword(self, keyword_name: str, language: str = None) -> dict|str :
        try:
            keywords = self.text_resources['keywords']
            return keywords[keyword_name] if not language else keywords[keyword_name][language]
        except:
            pass
        return None


    def handle(self, telegram_data: dict):
        # TODO: Complete this
        message: TelegramMessage | TelegramCallbackQuery = None
        user: VIPAccount = None
        response: TelegramMessage = None
        keyboard: Keyboard | InlineKeyboard = None
        dont_use_main_keyboard: bool = False
        if 'callback_query' in telegram_data:
            callback_query = TelegramCallbackQuery(telegram_data['callback_query'])
            user = callback_query.by
            if callback_query.action in self.callback_query_hanndlers:
                handler: Callable[[TelegramBotCore, TelegramCallbackQuery], Union[TelegramMessage, Keyboard|InlineKeyboard]]  = self.callback_query_hanndlers[callback_query.action]
                response, keyboard = handler(self, callback_query)
        else:
            message = TelegramMessage(telegram_data)
            user = message.by
            handler: Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]] = None
            if user.state != UserStates.NONE and user.state in self.state_handlers:
                handler = self.state_handlers[user.state]
                response, keyboard = handler(self, message)

            if not response:
                if message.text in self.message_handlers:
                    handler = self.message_handlers[message.text]
                    response, keyboard = handler(self, message)
        if not response:
            response = TelegramMessage.Text(target_chat_id=user.chat_id, text=self.text("wrong_command", user.language))

        if not keyboard and not dont_use_main_keyboard:
            keyboard = self.main_keyboard(user.language)
        self.send(message=response, keyboard=keyboard)



class TelegramBot(TelegramBotCore):
    '''Customizabvle part of bot'''
    def __init__(self, token: str, username: str, host_url: str, text_resources: dict, _main_keyboard: Dict[str, Keyboard]|Keyboard = None) -> None:
        super().__init__(token, username, host_url, text_resources, _main_keyboard)


    # Main Sections:
    def add_state_handler(self, handler: Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]], state: UserStates|int):
        self.state_handlers[state] = handler


    # Main Sections:
    def add_message_handler(self, handler: Callable[[TelegramBotCore, TelegramMessage], TelegramMessage], message: dict|list|str = None):
        '''Add message handlers; Provide specific messages in your desired languages (as dict) to call their provided handlers when that message is sent by user;'''
        # if your bot has multiple languages then notice that your language keys must match with these keys in message
        if message:
            if not isinstance(message, dict) and not isinstance(message, list):
                self.message_handlers[message] = handler
                return

            for lang in message:
                self.message_handlers[message[lang]] = handler
            return
        # TODO: ?if msg_texts if none, then the handler is global

    def add_command_handler(self, handler: Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]], command: str):
        self.command_handlers[f"/{command} " if command[0] != '/' else command] = handler


    def add_callback_query_handler(self, handler: Callable[[TelegramBotCore, TelegramCallbackQuery], TelegramMessage], action: str = None):
        self.callback_query_hanndlers[action] = handler
