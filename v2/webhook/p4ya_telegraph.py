from db.vip_account import VIPAccount
import requests
from tools.manuwriter import log


class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg = data['message']
        self.text =  self.msg['text']

        # self.by = VIPAccount.Get(self.msg['chat']['id'])
        self.chat_id = self.msg['chat']['id']

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
