
class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg = data
        self.text =  self.msg['text']
        self.user_id = self.msg['from']['id']
        self.chat_id = self.msg['chat']['id']
        self.username = self.msg['from']['username']
        self.user_firstname = self.msg['from']['first_name']

class TelegramBot:

