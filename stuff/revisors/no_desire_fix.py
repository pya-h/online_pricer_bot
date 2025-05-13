
from models.account import Account
from api.crypto_service import CoinMarketCap
from api.currency_service import SourceArena


x = CoinMarketCap('fuck')
y = SourceArena('1', '2')
chats = Account.Everybody()

for chat_id in chats:
    try:
        acc = Account.Get(chat_id)
        changed = False

        if acc.desired_coins:
            new_cryptos = list(filter(lambda token: token in CoinMarketCap.CoinsInPersian, acc.desired_coins))
            changed = len(new_cryptos) != len(acc.desired_coins)
            acc.desired_coins = new_cryptos
        if acc.desired_currencies:
            new_currs = list(filter(lambda token: token in SourceArena.CurrenciesInPersian, acc.desired_currencies))
            if not changed:
                changed = len(new_currs) != len(acc.desired_currencies)
            acc.desired_currencies = new_currs
        if changed:
            acc.save()
            print(acc.chat_id, 'Fixed.')
    except Exception as x:
        print(x)
