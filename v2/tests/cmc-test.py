from api.crypto_service import CoinMarketCap
from decouple import config


api_key = config('COINMARKETCAP_API_KEY')

cmc = CoinMarketCap(api_key)

while True:
    l = input('You coin symbol list separated by spaces ["x" for using default list]')
    data = cmc.send_request(custom_symbol_list=l.split() if l != 'x' else None)
    print(data)
    print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -\n')
