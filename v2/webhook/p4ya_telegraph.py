from db.vip_models import VIPAccount
import requests
from tools.manuwriter import log


class ForwardOrigin:
    def __init__(self, forward_data: dict) -> None:
        self.type = forward_data['type']
        self.id = None
        self.message_id = None
        self.title = None
        self.username = None
        if self.type == 'channel':
            self.id = forward_data['chat']['id']
            self.message_id = forward_data['message_id']
            self.title = forward_data['chat']['title']
            if 'username' in forward_data['chat']:
                self.username = forward_data['chat']['username']
        elif self.type == 'user':
            self.id = forward_data['sender_user']['id']
            self.title = forward_data['sender_user']['first_name']
            if 'username' in forward_data['sender_user']:
                self.username = forward_data['sender_user']['username']

    def __str__(self) -> str:
        return f"type: {self.type}\ntitle:{self.title}\nid:{self.id}\nusername:{self.username}"
class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg: dict = data['message']
        self.id: int = self.msg['message_id'] if 'message_id' in self.msg else None
        self.text: str =  self.msg['text']

        self.by: VIPAccount = VIPAccount.Get(self.msg['chat']['id'])
        self.chat_id: int = self.msg['chat']['id']
        self.forward_origin: ForwardOrigin = ForwardOrigin(self.msg['forward_origin']) if 'forward_origin' in self.msg else None

    @staticmethod
    def Create(target_chat_id: str, text: str):
        return TelegramMessage({"message": {
            "text": text,
            "chat": {
                "id": target_chat_id
            }
        }})

class TelegramBot:
    def __init__(self, token: str, username: str= 'unknownbot', host_url: str = 'localhost:5000') -> None:
        self.token = token
        self.bot_api_url = f"https://api.telegram.org/bot{self.token}"
        self.host_url = host_url
        self.username = username

    def send(self, message: TelegramMessage):
        url = f"{self.bot_api_url}/sendMessage"
        chat_id = message.chat_id # message.by.chat_id
        payload = {'chat_id': chat_id, 'text': message.text}
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log(f"User-Responding Failure => status code:{response.status_code}\n\tChatId:{message.by.chat_id}\nResponse text: {response.text}", category_name="VIP_FATAL")
        return response  # as dict

    def get_telegram_link(self) -> str:
        return f'https://t.me/{self.username}'
