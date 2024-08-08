from api.crypto_service import CoinMarketCapService
from api.currency_service import NavasanService, GoldService

coins = CoinMarketCapService.LoadPersianNames()

def count_them(target_dict: dict):
    max_symbol_word_count = 0
    max_name_word_count = 0
    for symbol in target_dict:
        symbol_word_count = len(symbol.split())
        if symbol_word_count > max_symbol_word_count:
            max_symbol_word_count = symbol_word_count
        name_word_count = len(target_dict[symbol].split())
        if name_word_count > max_name_word_count:
            max_name_word_count = name_word_count

    return max_symbol_word_count, max_name_word_count

s, n = count_them(coins)
print(s, " ", n)

x = GoldService('sss')
NavasanService.LoadPersianNames()

s, n = count_them(NavasanService.CurrenciesInPersian)
print(s, " ", n)


s, n = count_them(NavasanService.GoldsInPersian)
print(s, " ", n)
