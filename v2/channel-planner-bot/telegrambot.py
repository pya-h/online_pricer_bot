
class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg = data
        self.text =  self.msg['text']
        self.user_id = self.msg['from']['id']
        self.username = self.msg['from']['username']

        self.chat_id = self.msg['chat']['id']

class TelegramBot:
    pass
