from decouple import config
from db_interface import *
ADMIN_USERNAME = config('ADMIN_USERNAME')
ADMIN_PASSWORD = config('ADMIN_PASSWORD')


class Account:
    Instances = {}
    MaxDesiredCoins = 5
    MaxDesiredCurrencies = 10
    Database = DatabaseInterface.Get()
    @staticmethod
    def Get(chat_id):
        if chat_id in Account.Instances:
            return Account.Instances[chat_id]
        row = Account.Database.get(chat_id)
        if row:
            currs = row[1] if not row[1] or row[1][-1] != ";" else row[1][:-1]
            cryptos = row[2] if not row[2] or row[2][-1] != ";" else row[2][:-1]
            return Account(row[0], currs.split(";") if currs else [], cryptos.split(';') if cryptos else [])
        
        return Account(chat_id=chat_id)
        

    def save(self):
        Account.Database.add(self)
        # or update
        
    def __init__(self, chat_id, currencies=[], cryptos=[]) -> None:
        self.is_admin = False
        self.chat_id = chat_id
        self.desired_coins = cryptos
        self.desired_currencies = currencies
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

    def str_desired_coins(self):
        return ';'.join(self.desired_coins)

    def str_desired_currencies(self):
        return ';'.join(self.desired_currencies)