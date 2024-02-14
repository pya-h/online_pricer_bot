from db.vip_models import VIPAccount
import requests
from tools.manuwriter import log
from db.vip_models import UserStates
from typing import Callable, Dict, Union
from tools.mathematix import minutes_to_timestamp
from payagraph.containers import *
from payagraph.keyboards import *
from time import time
from tools.planner import Planner
from tools.exceptions import *


class ParallelJob:
    '''Define objects from this and use it in TelegramBot, it will does some parallel jobs in the bot by a specific interval [in minutes]'''
    def __init__(self, interval: int, function: Callable[..., any], *params) -> None:
        self.interval: int = interval
        self.function: Callable[..., any] = function
        self.last_run_result: any = None
        self.last_call_minutes: int = None
        self.params: list[any] = params
        self.running: bool = False


    def go(self):
        '''Start running...'''
        self.last_call_minutes = time() // 60
        self.running = True
        return self

    def do(self):
        self.last_run_result = self.function(*self.params)
        self.last_call_minutes = time() // 60

    def stop(self):
        self.running = False


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
        self.parallels: list[ParallelJob] = []
        self.clock = Planner(1.0, self.ticktock)


    def start_clock(self):
        '''Start the clock and handle(/run if needed) parallel jobs. As parallel jobs are optional, the clock is not running from start of the bot. it starts by direct demand of developer or user.'''
        self.clock.start()

    def stop_clock(self):
        '''Stop bot clock and all parallel jobs.'''
        self.clock.stop()


    def ticktock(self):
        '''Runs every 1 minutes, and checks if there's any parallel jobs and is it time to perform them by interval or not'''
        now = time() // 60
        print('tick tocked')
        ready_jobs = list(filter(
            lambda job: (job.running) and (now - job.last_call_minutes >= job.interval) , self.parallels
        ))

        for job in ready_jobs:
            job.do()

    def get_uptime(self) -> str:
        '''Bot being awake time, if the clock has not been stopped ofcourse'''
        return f'The bot\'s uptime is: {minutes_to_timestamp(self.clock.minutes_running())}'


    def main_keyboard(self, user_language: str = None) -> Keyboard:
        if isinstance(self._main_keyboard, Keyboard):
            return self._main_keyboard
        if isinstance(self._main_keyboard, dict):
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

    def edit(self, modified_message: TelegramMessage, keyboard: InlineKeyboard):
        '''Edits a message on telegram. Note: Should pass the exact message object extracted from telegram request but edittedt [text, photo, whatever]'''
        url = f"{self.bot_api_url}/editMessageText"
        chat_id = modified_message.chat_id # message.by.chat_id
        payload = {'chat_id': chat_id, 'text': modified_message.text, 'message_id': modified_message.id}
        if (keyboard):
            if not isinstance(keyboard, InlineKeyboard):
                raise InvalidKeyboardException('Only InlineKeyboard is allowed when editting a message.')
            keyboard.attach_to(payload)

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log(f"User-Responding Failure => status code:{response.status_code}\n\tChatId:{modified_message.by.chat_id}\nResponse text: {response.text}", category_name="VIP_FATAL")
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
        response: TelegramMessage| TelegramCallbackQuery = None
        keyboard: Keyboard | InlineKeyboard = None
        dont_use_main_keyboard: bool = False
        if 'callback_query' in telegram_data:
            message = TelegramCallbackQuery(telegram_data)
            user = message.by
            if message.action in self.callback_query_hanndlers:
                handler: Callable[[TelegramBotCore, TelegramCallbackQuery], Union[TelegramMessage, Keyboard|InlineKeyboard]]  = self.callback_query_hanndlers[message.action]
                response, keyboard = handler(self, message)
        else:
            message = TelegramMessage(telegram_data)
            user = message.by
            handler: Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]] = None
            if message.text in self.command_handlers:
                handler = self.command_handlers[message.text]
                response, keyboard = handler(self, message)
            else:
                if user.state != UserStates.NONE and user.state in self.state_handlers:
                    handler = self.state_handlers[user.state]
                    response, keyboard = handler(self, message)

                if not response:
                    if message.text in self.message_handlers:
                        handler = self.message_handlers[message.text]
                        response, keyboard = handler(self, message)
        if not response:
            response = TelegramMessage.Text(target_chat_id=user.chat_id, text=self.text("wrong_command", user.language))

        # if message != response or ((keyboard) and not isinstance(keyboard, InlineKeyboard)):
        if not response.replace_on_previous or ((keyboard) and not isinstance(keyboard, InlineKeyboard)):
            if not keyboard and not dont_use_main_keyboard:
                keyboard = self.main_keyboard(user.language)
            self.send(message=response, keyboard=keyboard)
        else:
            self.edit(message, keyboard)



class TelegramBot(TelegramBotCore):
    '''Customizabvle part of bot'''
    def __init__(self, token: str, username: str, host_url: str, text_resources: dict, _main_keyboard: Dict[str, Keyboard]|Keyboard = None) -> None:
        super().__init__(token, username, host_url, text_resources, _main_keyboard)


    # Main Sections:
    def add_state_handler(self, handler: Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]], state: UserStates|int):
        self.state_handlers[state] = handler

    # Main Sections:
    def add_message_handler(self, handler: Callable[[TelegramBotCore, TelegramMessage], Union[TelegramMessage, Keyboard|InlineKeyboard]], message: dict|list|str = None):
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
        self.command_handlers[f"/{command}" if command[0] != '/' else command] = handler


    def add_callback_query_handler(self, handler: Callable[[TelegramBotCore, TelegramCallbackQuery], Union[TelegramMessage, Keyboard|InlineKeyboard]], action: str = None):
        self.callback_query_hanndlers[action] = handler
