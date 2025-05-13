
from models.account import Account
from api.crypto_service import CoinMarketCapService
from api.currency_service import NavasanService
import time
from db.interface import DatabaseInterface
DatabaseInterface.get()
print('Allowing mysql to prepare itself...')
time.sleep(3)
x = CoinMarketCapService('temp')
y = NavasanService('temp', 'temp')
print('Starting migration...\nReading all users...')
chats = Account.sqliteEverybody()
print(f'{len(chats)} users read.')
successfulls = 0
for chat_id in chats:
    if chat_id <= 0:
        continue
    try:
        acc = Account.sqliteGet(chat_id)

        if acc.desired_cryptos:
            acc.desired_cryptos = list(filter(lambda token: token in CoinMarketCapService.coinsInPersian, acc.desired_cryptos))
        if acc.desired_currencies:
            acc.desired_currencies = list(filter(lambda token: token in NavasanService.currenciesInPersian, acc.desired_currencies))
        acc.save()
        print(acc.chat_id, 'Migrated.')
        successfulls += 1
    except Exception as x:
        print(x)
print(f'Finished.\n{successfulls} users data successfully migrated.')