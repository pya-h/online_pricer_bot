import coinmarketcapapi as cmc_api
from api.manager import *
from tools.exceptions import NoLatestDataException, InvalidInputException

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
    "BABYDOGE": "بیبی دوج کوین",
    "YFI": "یرن فایننس",
    "C98": "کوین 98",
    "CFX": "کانفلاکس",
    "LUNA": "ترا",
    "PEPE": "پپه",
    "SUI": "سویی",
}


# --------- COINGECKO -----------
class CoinGecko(APIManager):
    '''CoinGecko Class. The object of this class will get the cryptocurrency prices from coingecko.'''
    def __init__(self, params=None) -> None:
        # params = {
        #     'vs_currency': "usd",
        #     'order': "market_cap_desc",
        #     'per_page': 100,
        #     'page': 1,
        #     'sparkline': False,
        #     'price_change_percentage': "24h",
        # }
        super(CoinGecko, self).__init__(url='https://api.coingecko.com/api/v3/coins/list', source="CoinGecko.com",
                                        dict_persian_names=COINS_PERSIAN_NAMES, cache_file_name="coingecko.json")

    def extract_api_response(self, desired_coins=None, short_text=True):
        'Construct a text string consisting of each desired coin prices of a special user.'
        desired_coins = self.get_desired_ones(desired_coins)

        res = ''
        for coin in self.latest_data:
            symbol = coin['symbol'].upper()
            name = coin['name'] if symbol != 'USDT' else 'Tether'
            if symbol in desired_coins:
                price = coin['market_data']['current_price']['usd']
                res += self.crypto_description_row(name, symbol, price)

        if res:
            res = f'📌 #قیمت_لحظه_ای #بازار_ارز_دیجیتال 👇\n{res}'
        return res


# --------- COINMARKETCAP -----------
class CoinMarketCap(APIManager):
    '''CoinMarketCap Class. The object of this class will get the cryptocurrency prices from CoinMarketCap.'''

    def __init__(self, api_key, price_unit='USD', params=None) -> None:
        super(CoinMarketCap, self).__init__(
            url='https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest',
            source="CoinMarketCap.com", dict_persian_names=COINS_PERSIAN_NAMES, cache_file_name='coinmarketcap.json')
        self.api_key: str = api_key
        self.price_unit: str = price_unit
        self.symbols_list: str = None
        self.update_symbols_list()

    def update_symbols_list(self):
        '''Construct the list of all cryptocurrency coin symbols'''
        self.symbols_list = ''
        for cn in COINS_PERSIAN_NAMES:
            self.symbols_list += cn + ","
        self.symbols_list = self.symbols_list[:-1]  # remove last ','

    def set_price_unit(self, pu):
        self.price_unit = pu

    def send_request(self):
        '''Send request to coinmarketcap to receive the prices. This function differs from other .send_request methods from other BaseAPIManager childs'''
        cmc = cmc_api.CoinMarketCapAPI(self.api_key)
        latest_cap = cmc.cryptocurrency_quotes_latest(symbol=self.symbols_list, convert=self.price_unit)
        self.cache_data(
            json.dumps(latest_cap.data)
        )

        return latest_cap.data

    def extract_api_response(self, desired_coins=None, short_text=True):
        '''This function constructs a text string that in each row has the latest price of a
            cryptocurrency unit in two price units, Dollors and Tomans'''
        desired_coins = self.get_desired_ones(desired_coins)
        if not self.latest_data:
            raise NoLatestDataException('Use for anouncing prices!')

        res = ''
        for coin in desired_coins:
            price = self.latest_data[coin][0]['quote'][self.price_unit]['price']
            name = self.latest_data[coin][0]['name'] if coin != 'USDT' else 'Tether'
            res += self.crypto_description_row(name, coin, price, short_text=short_text)

        if res:
            res = f'📌 #قیمت_لحظه_ای #بازار_ارز_دیجیتال 👇\n{res}'
        return res


    def equalizer_row(self, unit_symbol: str, value: float|int):
        '''returns the row shape/format of the equalizing coin.'''
        value_cut = mathematix.cut_and_separate(value)
        value = mathematix.persianify(value_cut)
        return f'🔸 {value} {self.dict_persian_names[unit_symbol]}'

    def equalize(self, source_unit_symbol: str, amount: float|int, desired_coins: list = None) -> str:
        '''This function gets an amount param, alongside with a source_unit_symbol [and abviously with the users desired coins]
            and it returns a text string, that in each row of that, shows that amount equivalent in another cryptocurrency unit.'''
        # First check the required data is prepared
        if not self.latest_data:
            raise NoLatestDataException('Use for equalizing!')
        if not source_unit_symbol in self.latest_data:
            raise InvalidInputException('Coin symbol!')

        # text header
        res = f'📌 #معادل سازی 👇\nبا توجه به آخرین قیمت های بازار ارز دیجیتال ' + \
            mathematix.persianify(amount) + ' معادل است با:\n\n'
        # first row is the equivalent price in USD(the price unit selected by the bot configs.)
        absolute_amount = amount * float(self.latest_data[source_unit_symbol][0]['quote'][self.price_unit]['price']))
        res += self.equalizer_row(source_unit_symbol, absolute_amount)
        desired_coins = self.get_desired_ones(desired_coins)
        for coin in desired_coins:
            amount_in_this_ccoin_unit = absolute_amount  / float(self.latest_data[coin][0]['quote'][self.price_unit]['price'])
            res += self.equalizer_row(amount_in_this_ccoin_unit)

        return res
