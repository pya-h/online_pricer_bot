import coinmarketcapapi as cmc_api
from api_manager import *


COINS_PERSIAN_NAMES = {
    'BTC': 'بیت کوین',
    "ETH": 'اتریوم',
    'USDT': 'تتر',
    "BNB": 'بایننس کوین',
    'DOGE': 'دوج کوین',
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
    'SHIB': 'شیبا اینو',
    "LINK": "چین لینک",
    "ATOM": "کازماس",
    "UNI": "یونی سوآپ",
    "ICP": "اینترنت کامپیوتر",
    "ETC": "اتریوم کلاسیک",
    "TON": "تن کوین",
    "XLM": "استلار",
    "BCH": "بیت کوین کش",
    "FIL": "فایل کوین",
    "HBAR": "هدرا هشگراف",
    "APT": "آپتوس",
    "CRO": "کرونوس",
    "LDO": "لیدو دائو",
    "ARB": "آربیتروم",
    "NEAR": "نیر پروتکل",
    "VET": "وی چین",
    "APT": "ایپ کوین",
    "QNT": "کوانت",
    "ALGO": "آلگوراند",
    "GRT": "گراف",
    "FTM": "فانتوم",
    "EOS": "ایاس",
    "SAND": "سند باکس",
    "EGLD": "الروند",
    "MANA": "دسنترالند",
    "AAVE": "آوه",
    "THETA": "تتا نتورک",
    "STX": "استکس",
    "XTZ": "تزوس",
    "FLOW": "فلو",
    "AXS": "اکسی اینفینیتی",
    "CHZ": "چیلیز",
    "RNDR": "رندر توکن",
    "KCS": "کوکوین توکن",
    "NEO": "نئو",
    "CRV": "کرو دائو",
    "CSPR": "کسپر",
    "KLAY": "کلایتون",
    "OP": "اپتیمیسم",
    "MKR": "میکر",
    "LUNC": "لونا کلاسیک",
    "BSV": "ساتوشی ویژن",
    "SNX": "سینتتیکس",
    "INJ": "اینجکتیو",
    "ZEC": "زی کش",
    "BTT": "بیت تورنت",
    "MINA": "مینا",
    "XEC": "ای کش",
    "HT": "هیوبی توکن",
    "DASH": "دش",
    "MIOTA": "آیوتا",
    "PAXG": "پکس گلد",
    "CAKE": "پنکیک سوآپ",
    "GT": "گیت توکن",
    "TWT": "تراست ولت توکن",
    "FLR": "فلر",
    "LRC": "لوپرینگ",
    "ZIL": "زیلیکا",
    "WOO": "وو",
    "RUNE": "تورچین",
    "DYDX": "دی وای دی ایکس",
    "CVX": "کانوکس فایننس",
    "NEXO": "نکسو",
    "KAVA": "کاوا",
    "INJ": "انجین کوین",
    "1INCH": "وان اینچ",
    "OSMO": "اسموسیس",
    "BAT": "بت",
    "ROSE": "رز",
    "MASK": "ماسک نتورک",
    "FLOKI": "فلوکی اینو",
    "GALA": "گالا",
    "KSM": "کوساما",
    "ONE": "هارمونی",
    "HNT": "هلیوم",
    "AR": "آرویو",
    "GMT": "استپن",
    "SUSHI": "سوشی سوآپ",
    "KDA": "کادنا",
    "BabyDoge": "بیبی دوج کوین",
    "YFI": "یرن فایننس",
    "C98": "کوین 98",
    "CFX": "کانفلاکس",
    "LUNA": "ترا",
    "PEPE": "پپه",
    "SUI": "سویی",


    # "BLOK": "بلاک توپیا",
    # "FLUX": "فلاکس",
    # "MBOX": "موباکس",
    # "BRISE": "برایس",
    # "LEO": "لئو",
    # "OKB": "اوکی بی",
    # "RPL": "راکت پول",
    # "BIT": "بیت دائو",
    # "IMX": "ایمیوتیبل ایکس",
    # "GMX": "جی ام ایکس",
    # "ELON": "دوج ایلان مارس",
    # "ZEN": "هورایزن",
    # "ONT": "آنتولوژی",
    # "SC": "سیاکوین",
    # "HOT": "هولو",
    # "GLM": "گولم",
    # "ZRX": "زیرو ایکس پروتکل",
    # "KLV": "کلور",


}

# --------- COINGECKO -----------

class CoinGecko(APIManager):
    def __init__(self, params=None) -> None:
        # params = {
        #     'vs_currency': "usd",
        #     'order': "market_cap_desc",
        #     'per_page': 100,
        #     'page': 1,
        #     'sparkline': False,
        #     'price_change_percentage': "24h",
        # }
        super(CoinGecko, self).__init__(url='https://api.coingecko.com/api/v3/coins/', source="CoinGecko.com", dict_persian_names=COINS_PERSIAN_NAMES)

    def extract_api_response(self, desired_coins):
        desired_coins = self.get_desired_ones(desired_coins)

        res = ''
        for coin in self.latest_data:
            name = coin['name']
            symbol = coin['symbol'].upper()
            if symbol in desired_coins:
                price = coin['market_data']['current_price']['usd']
                res += self.crypto_description_row(name, symbol, price)

        return self.signed_message(res)



# --------- COINMARKETCAP -----------
class CoinMarketCap(APIManager):

    def __init__(self, api_key, price_unit='USD', params=None) -> None:
        super(CoinMarketCap, self).__init__(url='https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest', source="CoinMarketCap.com", dict_persian_names=COINS_PERSIAN_NAMES)
        self.api_key = api_key
        self.price_unit = price_unit
        self.symbols_list = None
        self.update_symbols_list()

    def update_symbols_list(self):
        self.symbols_list = ''
        for cn in COINS_PERSIAN_NAMES:
            self.symbols_list += cn + ","
        self.symbols_list = self.symbols_list[:-1]  #remove last ','

    def set_price_unit(self, pu):
        self.price_unit = pu

    def send_request(self):
        cmc = cmc_api.CoinMarketCapAPI(self.api_key)
        latest_cap = cmc.cryptocurrency_quotes_latest(symbol=self.symbols_list, convert=self.price_unit)
        return latest_cap.data

        # other useful functions
        # print(cmc.cryptocurrency_info(symbol="BTC"))

        # print(cmc.cryptocurrency_map().data[0])

        # dict_cap = json.loads(latest_cap)
        # usd = latest_cap.data['BTC'][0]['quote']['USD']['price']
        # usd2 = latest_cap.data['ETH'][0]['quote']['USD']['price']


    def extract_api_response(self, desired_coins):
        desired_coins = self.get_desired_ones(desired_coins)

        res = ''
        if self.latest_data:
            for coin in desired_coins:
                price = self.latest_data[coin][0]['quote'][self.price_unit]['price']
                name = self.latest_data[coin][0]['name']
                res += self.crypto_description_row(name, coin, price)
        return self.signed_message(res)

    # def send_request_classic(self):
    #     from requests import Request, Session
    #     from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
    #     parameters = {
    #         'start':'1',
    #         'limit':'5000',
    #         'convert': self.price_unit,
    #     }
    #     headers = {
    #         'Accepts': 'application/json',
    #         'X-CMC_PRO_API_KEY': self.api_key,
    #     }

    #     session = Session()
    #     session.headers.update(headers)

    #     try:
    #         response = session.get(CoinMarketCap.URL, params=parameters)
    #         data = json.loads(response.text)
    #         return data
    #     except (ConnectionError, Timeout, TooManyRedirects) as e:
    #         print(e)


