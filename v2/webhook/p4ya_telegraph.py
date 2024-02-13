from db.vip_models import VIPAccount
import requests, json
from tools.manuwriter import log
from enum import Enum
from math import ceil
from webhook.p4ya_telegraph_basics import CanBeKeyboardItemInterface


class ChatTypes(Enum):
    USER = "user"
    CHANNEL = "channel"
    GROUP = "group"


class ForwardOrigin:
    def __init__(self, forward_data: dict) -> None:
        self.type: ChatTypes = forward_data['type']
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
    def Arrange(list_of_keys: list[CanBeKeyboardItemInterface]):
        keys_count = len(list_of_keys)
        keys = [[ InlineKey(list_of_keys[i][j].title(), list_of_keys[i][j].value()) for j in range(i * 5, (i + 1) * 5 if (i + 1) * 5 < keys_count else keys_count)] \
            for i in range(ceil(keys_count // 5))]
        return InlineKeyboard(keys)


class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg: dict = data['message']
        self.id: int = self.msg['message_id'] if 'message_id' in self.msg else None
        self.text: str =  self.msg['text']

        self.by: VIPAccount = VIPAccount.Get(self.msg['chat']['id'])
        self.chat_id: int = self.msg['chat']['id']
        self.forward_origin: ForwardOrigin = ForwardOrigin(self.msg['forward_origin']) if 'forward_origin' in self.msg else None

    @staticmethod
    def Create(target_chat_id: str, text: str = ''):
        return TelegramMessage({"message": {
            "text": text,
            "chat": {
                "id": target_chat_id
            }
        }})


class TelegramBot:
    def __init__(self, token: str, username: str, host_url: str, text_resources: dict) -> None:
        self.token = token
        self.bot_api_url = f"https://api.telegram.org/bot{self.token}"
        self.host_url = host_url
        self.username = username
        self.text_resources: dict = text_resources  # this is for making add multi-language support to the bot
        self.handlers: list[dict] = []  # bot handlers, fills with add_handler
        # these handler will be checked when running bot.handle

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

    def getext(self, text_key: str, language: str = 'fa') -> str:  # short for gettext
        try:
            return self.text_resources[text_key][language]
        except:
            pass
        return "پاسخ نامعلوم" if language == 'fa' else "Unknown response"


    # Main Sections:
    def add_handler(command_text: str, handler: any):
        # TODO: Complete this
        pass

    def handle(user: VIPAccount, message: TelegramMessage):
        # TODO: Complete this
        pass
