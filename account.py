from decouple import config
ADMIN_USERNAME = config('ADMIN_USERNAME')
ADMIN_PASSWORD = config('ADMIN_PASSWORD')


class Account:
    Instances = {}

    @staticmethod
    def Get(chat_id):
        if not chat_id in Account.Instances:
            return Account(chat_id=chat_id)
        return Account.Instances[chat_id]

    def __init__(self, chat_id) -> None:
        self.is_admin = False
        self.chat_id = chat_id
        self.desired_coins = []
        self.desired_currencies = []
        Account.Instances[chat_id] = self

    def authorization(self, args):
        if self.is_admin:
            return True

        if args and len(args) >= 2:
            username = args[0]
            password = args[1]
            self.is_admin = password == ADMIN_PASSWORD and username == ADMIN_USERNAME
            return self.is_admin

        return False

    @staticmethod
    def Leave(chat_id):
        if chat_id in Account.Instances:
            del Account.Instances[chat_id]

    def __del__(self):
        print(f'Account #{self.chat_id} has been destroyed and freed...')
