import json
import requests
import coinmarketcapapi as cmc_api


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

class CoinGecko:
    URL = 'https://api.coingecko.com/api/v3/coins/'
    Source = "CoinGecko"
    def __init__(self, desired_coins, params=None) -> None:
        # params = {
        #     'vs_currency': "usd",
        #     'order': "market_cap_desc",
        #     'per_page': 100,
        #     'page': 1,
        #     'sparkline': False,
        #     'price_change_percentage': "24h",
        # }
        self.params = params
        self.desired_coins = desired_coins
        self.latest_data = ''

    def set_params(self, pms):
        self.params = pms

    def extract_desired_prices(self, data):
        res = ''
        for coin in data:
            name = coin['name']
            symbol = coin['symbol'].upper()
            if symbol in self.desired_coins:
                price = coin['market_data']['current_price']['usd']
                res += '🔸 %s (%s): %.3f$\n%s: %d دلار\n\n' % (name, symbol, price, COIN_NAMES[symbol], price*10000)
        return res

    def get(self):
        self.latest_data = self.send_request()
        return self.extract_desired_prices(self.latest_data)

    def get_latest(self):
        return self.extract_desired_prices(self.latest_data)


    # --------- COINGECKO -----------
    def send_request(self):
        response = requests.get(CoinGecko.URL, json=self.params)
        data = json.loads(response.text)
        return data


# --------- COINMARKETCAP -----------
class CoinMarketCap:
    URL = 'https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    Source = "CoinMarkerCap"

    def set_desired_coins(self, c_names):
        self.desired_coins = c_names
        self.update_symbols_list()

    def update_symbols_list(self):
        self.symbols_list = ''
        for cn in COIN_NAMES:
            self.symbols_list += cn + ","
        self.symbols_list = self.symbols_list[:-1]  #remove last ','


    def __init__(self, api_key, desired_coins, price_unit='USD') -> None:
        self.api_key = api_key
        self.price_unit = price_unit
        self.desired_coins = desired_coins
        self.symbols_list = None
        self.latest_data = ''
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


    def extract_desired_prices(self, data):
        res = ''
        for coin in self.desired_coins:
            price = data[coin][0]['quote'][self.price_unit]['price']
            name = data[coin][0]['name']
            res += '🔸 %s (%s): %.3f$\n%s: %d دلار\n\n' % (name, coin, price, COIN_NAMES[coin], price*10000)
        return res


    def get(self):
        self.latest_data = self.send_request() # update latest
        return self.extract_desired_prices(self.latest_data)  # then make message

    def get_latest(self):
        return self.extract_desired_prices(self.latest_data)

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


