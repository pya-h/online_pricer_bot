import json
import requests
import coinmarketcapapi as cmc_api

class CoinGecko:
    URL = 'https://api.coingecko.com/api/v3/coins/'

    def __init__(self, coin_names, params=None) -> None:
        # params = {
        #     'vs_currency': "usd",
        #     'order': "market_cap_desc",
        #     'per_page': 100,
        #     'page': 1,
        #     'sparkline': False,
        #     'price_change_percentage': "24h",
        # }
        self.params = params
        self.coin_names = coin_names
        self.latest_prices = ''


    def set_params(self, pms):
        self.params = pms

    def get(self):
        coins = self.send_request()
        self.latest_prices = ''
        for coin in coins:
            name = coin['name']
            symbol = coin['symbol'].upper()
            if symbol in self.coin_names:
                price = coin['market_data']['current_price']['usd']
                self.latest_prices += f'🔸 {name} ({symbol}): {price}$\n{self.coin_names[symbol]}: {price} دلار\n\n'
        return self.latest_prices

    # --------- COINGECKO -----------
    def send_request(self):
        response = requests.get(CoinGecko.URL, json=self.params)
        data = json.loads(response.text)
        return data


# --------- COINMARKETCAP -----------
class CoinMarketCap:
    URL = 'https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'

    def set_coin_names(self, c_names):
        self.coin_names = c_names
        self.update_symbols_list()

    def update_symbols_list(self):
        self.symbols_list = ''
        for cn in self.coin_names:
            self.symbols_list += cn + ","
        self.symbols_list = self.symbols_list[:-1]  #remove last ','


    def __init__(self, api_key, coin_names, price_unit='USD') -> None:
        self.api_key = api_key
        self.price_unit = price_unit
        self.coin_names = coin_names
        self.symbols_list = None
        self.latest_prices = ''
        self.update_symbols_list()

    def set_price_unit(self, pu):
        self.price_unit = pu

    def send_request(self):
        cmc = cmc_api.CoinMarketCapAPI(self.api_key)

        # print(cmc.cryptocurrency_info(symbol="BTC"))

        # print(cmc.cryptocurrency_map().data[0])

        latest_cap = cmc.cryptocurrency_quotes_latest(symbol=self.symbols_list, convert=self.price_unit)
        # dict_cap = json.loads(latest_cap)
        # usd = latest_cap.data['BTC'][0]['quote']['USD']['price']
        # usd2 = latest_cap.data['ETH'][0]['quote']['USD']['price']
        return latest_cap.data


    def get(self):
        data = self.send_request()
        self.latest_prices = ''
        for coin in self.coin_names:
            price = data[coin][0]['quote'][self.price_unit]['price']
            name = data[coin][0]['name']

            self.latest_prices += f'🔸 {name} ({coin}): {price}$\n{self.coin_names[coin]}: {price} دلار\n\n'
        return self.latest_prices

    def send_request_classic(self):
        from requests import Request, Session
        from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
        parameters = {
            'start':'1',
            'limit':'5000',
            'convert': self.price_unit,
        }
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.api_key,
        }

        session = Session()
        session.headers.update(headers)

        try:
            response = session.get(CoinMarketCap.URL, params=parameters)
            data = json.loads(response.text)
            return data
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)


