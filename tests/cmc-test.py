from api.crypto_service import CoinMarketCapService
from decouple import config
from json import dumps


api_key = config('COINMARKETCAP_API_KEY')

cmc = CoinMarketCapService(api_key)

def save(data: dict):
    f = open('api-result.json', 'w')
    f.write(dumps(data))
    f.close()
    
while True:
    l = input('You coin symbol list separated by spaces ["x" for using default list]')
    data = cmc.get_request(custom_symbol_list=l.split() if l != 'x' else None)
    save(data)
    print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -\n')
