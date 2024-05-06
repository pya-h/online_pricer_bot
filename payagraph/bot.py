import requests
from tools.manuwriter import log
from plus.models.account import UserStates, AccountPlus
from typing import Callable, Dict, Union
from tools.mathematix import minutes_to_timestamp
from payagraph.containers import *
from payagraph.keyboards import *
from time import time
from tools.planner import Planner
from tools.exceptions import *
from flask import Flask, request, jsonify
from payagraph.job import ParallelJob
from payagraph.keyboards import InlineKeyboard


class TelegramBotCore:
    ''' Main and static part of the class; Can be used to create bots without using handler funcionalities; user state management, message and command check and all other stuffs are on developer. handle function has no use in this mode of bot development.'''
    def __init__(self, token: str, host_url: str) -> None:
        self.token = token
        self.bot_api_url = f"https://api.telegram.org/bot{self.token}"
        self.host_url = host_url

    def send(self, message: GenericMessage, keyboard: Keyboard|InlineKeyboard = None):
        '''Calls the Telegram send message api.'''
        url = f"{self.bot_api_url}/sendMessage"
        chat_id = message.chat_id
        payload = {'chat_id': chat_id, 'text': message.text}
        if keyboard:
            keyboard.attach_to(payload)
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log(f"User-Responding Failure => status code:{response.status_code}\n\tChatId:{chat_id}\nResponse text: {response.text}", category_name="PLUS_FATALITY")
        return response  # as dict

    def edit(self, modified_message: GenericMessage, keyboard: InlineKeyboard):
        '''Edits a message on telegram. it will be called by .handle function when GenericMessage.replace_on_previous is True [text, photo, whatever]'''
        url = f"{self.bot_api_url}/editMessageText"
        chat_id = modified_message.chat_id
        payload = {'chat_id': chat_id, 'text': modified_message.text, 'message_id': modified_message.id}
        if keyboard:
            if not isinstance(keyboard, InlineKeyboard):
                raise InvalidKeyboardException('Only InlineKeyboard is allowed when editting a message.')
            keyboard.attach_to(payload)

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log(f"User-Responding Failure => status code:{response.status_code}\n\tChatId:{chat_id}\nResponse text: {response.text}", category_name="PLUS_FATALITY")
        return response  # as dict

    def answer_callback_query(self, callback_query_id: int, text: str, show_alert: bool = False, cache_time_sec: int = None, url_to_be_opened: str = None):
        '''Shows a toast or popup when dealing whit callback queries. If the callback query message menu is not editted its better to call this method.'''
        url = f"{self.bot_api_url}/answerCallbackQuery"
        payload = {'callback_query_id': callback_query_id, 'text': text, 'show_alert': show_alert}

        if cache_time_sec:
            payload['cache_time'] = cache_time_sec

        if url_to_be_opened:
            payload['url'] = url_to_be_opened

        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log(f"answerCallbackQuery Failure => status code:{response.status_code}\n\callback_query_id:{callback_query_id}\ncallback_query_text:{text}\nResponse text: {response.text}", category_name="PLUS_FATALITY")
        return response



class TelegramBot(TelegramBotCore):
    '''More Customizable and smart part of the TelegramBot; This object will allow to add handlers that are used by TelegramBotCore.handle function and
        by calling .handle function make the bot to handle user messages automatically, of sorts.'''
    def __init__(self, token: str, username: str, host_url: str, text_resources: dict, _main_keyboard: Dict[str, Keyboard]|Keyboard = None) -> None:
        super().__init__(token, host_url)
        self.bot_username = username
        self._main_keyboard: Dict[str, Keyboard]|Keyboard = _main_keyboard
        self.middlewares: list[Callable[[TelegramBotCore, dict], bool]] = [] # middlewares run before everything when a message is sent
        # if all middlewares returned True, bot is allowed to continue handling a message
        # This is useful for implement channel memberships and plus checks
        self.text_resources: dict = text_resources  # this is for making add multi-language support to the bot

        self.state_handlers: Dict[UserStates, Callable[[TelegramBotCore, GenericMessage], Union[GenericMessage, Keyboard|InlineKeyboard]]] = dict()
        self.command_handlers: Dict[str, Callable[[TelegramBotCore, GenericMessage], Union[GenericMessage, Keyboard|InlineKeyboard]]] = dict()
        self.message_handlers: Dict[str, Callable[[TelegramBotCore, GenericMessage], Union[GenericMessage, Keyboard|InlineKeyboard]]] = dict()  # bot handlers, fills with add_handler
        self.callback_query_hanndlers: Dict[str, Callable[[TelegramBotCore, TelegramCallbackQuery], Union[GenericMessage, Keyboard|InlineKeyboard]]] = dict()
        # these handler will be checked when running bot.handle
        self.cancel_keys: list = []  # Keywords that if the user sends them, in every state and condition, everything cancels out and user returns back to main menu
        self.parallels: list[ParallelJob] = []
        self.clock = None
        ### Flask App configs ###
        self.app: Flask = Flask(__name__)


    def main_keyboard(self, user_language: str = None) -> Keyboard:
        '''Get the keyboard that must be shown in most cases and on Start screen.'''
        if isinstance(self._main_keyboard, Keyboard):
            return self._main_keyboard
        if isinstance(self._main_keyboard, dict):
            if not user_language or user_language not in self._main_keyboard:
                return self._main_keyboard.values()[0]
            return self._main_keyboard[user_language]
        return None

    def get_telegram_link(self) -> str:
        return f'https://t.me/{self.bot_username}'

    def config_webhook(self, webhook_path = '/'):
        # **Telegram hook route**
        @self.app.route(webhook_path, methods=['POST'])
        def main_route():
            # code below must be add to middlewares
            allowed_to_continue = True
            for middleware in self.middlewares:
                allowed_to_continue = allowed_to_continue and middleware(self, request.json)

            if allowed_to_continue:
                self.handle(request.json)
            return jsonify({'status': 'ok'})

    def go(self, debug=False):
        self.app.run(debug=debug)

    def text(self, text_key: str, language: str = None) -> str|dict:  # short for gettext
        '''resource function: get an specific text from the texts_resources json loaded into bot object'''
        try:
            return self.text_resources[text_key][language] if language else self.text_resources[text_key]
        except:
            pass
        return "پاسخ نامعلوم" if language == 'fa' else "Unknown response"

    def keyword(self, keyword_name: str, language: str = None) -> dict|str :
        '''resource function: get an specific keyword(words that when sent to the bot will run a special function) from the texts_resources json loaded into bot object'''
        try:
            keywords = self.text_resources['keywords']
            return keywords[keyword_name] if not language else keywords[keyword_name][language]
        except:
            pass
        return None

    def cmd(self, command: str) -> str :
        '''resource function: get an specific command(english keywords starting with '/' that will run a special function) from the texts_resources json loaded into bot object'''
        try:
            return self.text_resources['commands'][command]
        except:
            pass
        return None
    def start_clock(self):
        '''Start the clock and handle(/run if needed) parallel jobs. As parallel jobs are optional, the clock is not running from start of the bot. it starts by direct demand of developer or user.'''
        self.clock = Planner(1.0, self.ticktock)
        self.clock.start()

    def stop_clock(self):
        '''Stop bot clock and all parallel jobs.'''
        self.clock.stop()

    def ticktock(self) -> int:
        '''Runs every 1 minutes, and checks if there's any parallel jobs and is it time to perform them by interval or not'''
        now = time() // 60
        print('tick tocked')

        for job in self.parallels:
            if (job.running) and (now - job.last_call_time >= job.interval):
                job.do()
        return now  # return current time

    def get_uptime(self) -> str:
        '''Bot being awake time, if the clock has not been stopped ofcourse'''
        return f'The bot\'s uptime is: {minutes_to_timestamp(self.clock.minutes_running())}'


    def add_cancel_key(self, key: str|dict):
        self.cancel_keys.extend(key.values() if isinstance(key, dict) else [key])

    # Main Sections:
    def add_state_handler(self, handler: Callable[[TelegramBotCore, GenericMessage], Union[GenericMessage, Keyboard|InlineKeyboard]], state: UserStates|int):
        '''Add a handler for special states of user. Depending on the appliance and structure of the bot, it must have its own UserStates enum, that you must add handler for each value of the enum. States are useful when getting multiple inputs for a model, or when special actions must be taken other than normal handlers'''
        self.state_handlers[state] = handler

    # Main Sections:
    def add_message_handler(self, handler: Callable[[TelegramBotCore, GenericMessage], Union[GenericMessage, Keyboard|InlineKeyboard]], message: dict|list|str = None):
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

    def add_command_handler(self, handler: Callable[[TelegramBotCore, GenericMessage], Union[GenericMessage, Keyboard|InlineKeyboard]], command: str):
        '''Add a Handler for a message starting with forthslash(/), so if the user sends that command, this handler will run.'''
        self.command_handlers[f"/{command}" if command[0] != '/' else command] = handler


    def add_callback_query_handler(self, handler: Callable[[TelegramBotCore, TelegramCallbackQuery], Union[GenericMessage, Keyboard|InlineKeyboard]], action: str = None):
        '''Add handler for each action value of the inline callback keyboards. Each group of inline keyboards have a spacial CallbackQuery.action, that each action value has its special handler '''
        self.callback_query_hanndlers[action] = handler

    def add_parallel_job(self, job: ParallelJob) -> bool:
        '''Add new parallel job to the bot; return False if the job Already exists.'''
        if job not in self.parallels:
            self.parallels.append(job)
            return True
        return False

    def add_middleware(self, middleware: Callable[[TelegramBotCore, dict], bool]):
        self.middlewares.append(middleware)

    def prepare_new_parallel_job(self, interval: int, functionality: Callable[..., any], *params) -> ParallelJob:
        '''Create a new ParallelJob object and then add it to bot parallel job list and start it.'''
        job = ParallelJob(interval, functionality, *params)
        self.add_parallel_job(job)
        return job.go()

    def handle(self, telegram_data: dict):
        '''determine what course of action to take based on the message sent to the bot by user. First command/message/state handler and middlewares and then call the handle with telegram request data.'''
        message: GenericMessage | TelegramCallbackQuery = None
        user: AccountPlus = None
        response: GenericMessage| TelegramCallbackQuery = None
        keyboard: Keyboard | InlineKeyboard = None
        dont_use_main_keyboard: bool = False
        # TODO: run middlewares first
        if isinstance(telegram_data, str):
            telegram_data = json.loads(telegram_data)

        if 'callback_query' not in telegram_data and 'message' not in telegram_data:
            # TODO: Check out what are these messages and handle them
            print('UNKNOWN FROM NOWHERE MESSAGE')
            return

        if 'callback_query' in telegram_data:
            message = TelegramCallbackQuery(telegram_data)
            user = message.by
            if message.action in self.callback_query_hanndlers:
                handler: Callable[[TelegramBotCore, TelegramCallbackQuery], Union[GenericMessage, Keyboard|InlineKeyboard]]  = self.callback_query_hanndlers[message.action]
                response, keyboard = handler(self, message)
                if not response.replace_on_previous:
                    self.answer_callback_query(message.callback_id, response.text, cache_time_sec=1)
        else:
            message = GenericMessage(telegram_data)
            user = message.by
            handler: Callable[[TelegramBotCore, GenericMessage], Union[GenericMessage, Keyboard|InlineKeyboard]] = None
            if message.text in self.cancel_keys:
                # Cancel out everything
                user.change_state()
                response = GenericMessage.Text(user.chat_id, self.text('what_todo', user.language))
            elif message.text in self.command_handlers:
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
            response = GenericMessage.Text(target_chat_id=user.chat_id, text=self.text("wrong_command", user.language))

        # if message != response or ((keyboard) and not isinstance(keyboard, InlineKeyboard)):
        if not response.replace_on_previous or ((keyboard) and not isinstance(keyboard, InlineKeyboard)):
            if not keyboard and not dont_use_main_keyboard:
                keyboard = self.main_keyboard(user.language)
            self.send(message=response, keyboard=keyboard)
        else:
            self.edit(message, keyboard)
