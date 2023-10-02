from decouple import config
from db_interface import *
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import tools


ADMIN_USERNAME = config('ADMIN_USERNAME')
ADMIN_PASSWORD = config('ADMIN_PASSWORD')

GARBAGE_COLLECT_INTERVAL = 60

#*******************************
# TODO: PUT LAST INTERACTION IN DATABASE, FOR COLLECTING USER STATISTICS
#*******************************
class Account:
    Instances = {}
    MaxSelectionInDesiredOnes = 20
    Database = DatabaseInterface.Get()
    Scheduler = None
    @staticmethod
    def GarbageCollect():
        now = datetime.now()
        garbage = []
        for chat_id in Account.Instances:
            if (now - Account.Instances[chat_id].last_interaction).total_seconds() / 60 >= GARBAGE_COLLECT_INTERVAL / 2:
                garbage.append(chat_id)
        # because changing dict size in a loop on itself causes error,
        # we first collect redundant chat_id s and then delete them from the memory
        for g in garbage:
            del Account.Instances[g]
        # tools.log("Garbage's been collected successfully")

    @staticmethod
    def Get(chat_id):
        if chat_id in Account.Instances:
            Account.Instances[chat_id].last_interaction = datetime.now()
            return Account.Instances[chat_id]
        row = Account.Database.get(chat_id)
        if row:
            currs = row[1] if not row[1] or row[1][-1] != ";" else row[1][:-1]
            cryptos = row[2] if not row[2] or row[2][-1] != ";" else row[2][:-1]
            return Account(row[0], currs.split(";") if currs else [], cryptos.split(';') if cryptos else [])

        return Account(chat_id=chat_id)


    def save(self):
        Account.Database.update(self)


    def __init__(self, chat_id, currencies=[], cryptos=[]) -> None:
        self.is_admin = False
        self.chat_id = chat_id
        self.desired_coins = cryptos[:]
        self.desired_currencies = currencies[:]
        self.last_interaction = datetime.now()
        Account.Instances[chat_id] = self  # this is for optimizing bot performance
        # saving recent users in the memory will reduce the delays for getting information, vs. using database everytime

        if not Account.Scheduler:
            # start garbage collector to optimize memory use
            Account.Scheduler = BackgroundScheduler()
            Account.Scheduler.add_job(Account.GarbageCollect, 'interval', seconds=GARBAGE_COLLECT_INTERVAL*60)
            Account.Scheduler.start()

    def __str__(self) -> str:
        return f'{self.chat_id}'

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
        tools.log(f'Account #{self.chat_id} has been destroyed and freed...')

    def str_desired_coins(self):
        return ';'.join(self.desired_coins)

    def str_desired_currencies(self):
        return ';'.join(self.desired_currencies)
