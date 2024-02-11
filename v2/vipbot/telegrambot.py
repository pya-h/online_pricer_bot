from vipbot.db.vip_account import VIPAccount
import requests
from tools.manuwriter import log


class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg = data
        self.text =  self.msg['text']

        self.by = VIPAccount.Get(self.msg['chat']['id'])


class TelegramBot:
    def __init__(self, token: str) -> None:
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{self.token}"


    def send(self, message: TelegramMessage):
        url = f"{self.base_url}/sendMessage"
        payload = {'chat_id': message.by.chat_id, 'text': message.text}
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            log(f"User-Responding Failure => status code:{response.status_code}\n\tChatId:{message.by.chat_id}\nResponse text: {response.text}", category_name="VIP_FATAL")
        return response  # as dict
