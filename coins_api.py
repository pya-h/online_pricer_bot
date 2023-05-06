import json
import requests
import coinmarketcapapi as cmc_api

USD_TO_TOMANS_RATE = 53000
COIN_NAMES = {
    'BTC': 'بیت کوین',
    "ETH": 'اتریوم',
    'USDT': 'تتر',
    "BNB": 'بایننس کوین',
    'XRP': 'ریپل',
    "ADA": 'کاردانو',
    'SOL': 'سولانا',
    "MATIC": 'پالیگان',
    'DOT': 'پولکادات',
    "TRX": 'ترون',
    'AVAX': 'آوالانچ',
    "LTC": 'لایت کوین',
    'BCH': 'بیت کوین کش',
    "XMR": 'مونرو',
    'DOGE': 'دوج کوین',
    'SHIB': 'شیبا اینو'
}

MAX_COIN_SELECTION = len(COIN_NAMES)

class CoinGecko:
    URL = 'https://api.coingecko.com/api/v3/coins/'
    Source = "CoinGecko"
    def __init__(self, params=None) -> None:
        # params = {
        #     'vs_currency': "usd",
        #     'order': "market_cap_desc",
        #     'per_page': 100,
        #     'page': 1,
        #     'sparkline': False,
        #     'price_change_percentage': "24h",
        # }
        self.params = params
        self.latest_data = ''

    def set_params(self, pms):
        self.params = pms

    def extract_prices(self, data, desired_coins):
        if not desired_coins:
            desired_coins = list(COIN_NAMES.keys())[:MAX_COIN_SELECTION]
        res = ''
        for coin in data:
            name = coin['name']
            symbol = coin['symbol'].upper()
            if symbol in desired_coins:
                price = coin['market_data']['current_price']['usd']
                res += '🔸 %s (%s): %.3f$\n%s: %d تومان\n\n' % (name, symbol, price, COIN_NAMES[symbol], price*USD_TO_TOMANS_RATE)
        return res + f"\n\nمنبع: {CoinGecko.Source}"


    def get(self, desired_coins=None):
        self.latest_data = self.send_request() # update latest
        return self.extract_prices(self.latest_data, desired_coins)  # then make message

    def get_latest(self, desired_coins=None):
        return self.extract_prices(self.latest_data, desired_coins)

    # --------- COINGECKO -----------
    def send_request(self):
        response = requests.get(CoinGecko.URL, json=self.params)
        data = json.loads(response.text)
        return data


# --------- COINMARKETCAP -----------
class CoinMarketCap:
    URL = 'https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    Source = "CoinMarketCap"

    def update_symbols_list(self):
        self.symbols_list = ''
        for cn in COIN_NAMES:
            self.symbols_list += cn + ","
        self.symbols_list = self.symbols_list[:-1]  #remove last ','


    def __init__(self, api_key, price_unit='USD') -> None:
        self.api_key = api_key
        self.price_unit = price_unit
        self.symbols_list = None
        self.latest_data = None
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


    def extract_prices(self, data, desired_coins):
        if not desired_coins:
            desired_coins = list(COIN_NAMES.keys())[:MAX_COIN_SELECTION]

        res = ''
        for coin in desired_coins:
            price = data[coin][0]['quote'][self.price_unit]['price']
            name = data[coin][0]['name']
            res += '🔸 %s (%s): %.3f$\n%s: %d تومان\n\n' % (name, coin, price, COIN_NAMES[coin], price*USD_TO_TOMANS_RATE)
        return res + f"\n\nمنبع: {CoinMarketCap.Source}"


    def get(self, desired_coins=None):
        self.latest_data = self.send_request() # update latest
        return self.extract_prices(self.latest_data, desired_coins)  # then make message

    def get_latest(self, desired_coins=None):
        return self.extract_prices(self.latest_data, desired_coins)

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


