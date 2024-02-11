from db.account import Account, UserStates
from vipbot.db.vip_interface import VIPDatabaseInterface


class VIPAccount(Account):

    MaxSelectionInDesiredOnes = 20
    Database = VIPDatabaseInterface.Get()
    Scheduler = None

    Instances = {}  # active accounts will cache into this; so there's no need to access database everytime
    # causing a slight enhancement on performance
    def __init__(self, chat_id: int, currencies: list=None, cryptos: list=None, language: str = 'fa') -> None:
        super().__init__(chat_id, currencies, cryptos, language)
