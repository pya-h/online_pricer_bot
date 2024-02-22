import coinmarketcapapi as cmc_api
from api.manager import *
from tools.exceptions import NoLatestDataException, InvalidInputException
from api.currency import SourceArena


# Parent Class
class CryptoCurrency(APIManager):
    CoinsInPersian = None

    @staticmethod
    def get_persian_coin_names() -> dict:
        coins_fa = "{}"
        try:
            persian_coin_names_file = open("./api/coins.fa.json", "r")
            coins_fa = persian_coin_names_file.read()
            persian_coin_names_file.close()
        except:
            pass
        return json.loads(coins_fa)

    def __init__(self, url: str, source: str, max_desired_selection: int = 5, params=None, cache_file_name: str = None) -> None:
        super().__init__(url, source, max_desired_selection, params, cache_file_name)
        if not CryptoCurrency.CoinsInPersian:
            CryptoCurrency.CoinsInPersian = CryptoCurrency.get_persian_coin_names()

    def get_desired_ones(self, desired_ones: list):
        if not desired_ones:
            desired_ones = list(CryptoCurrency.CoinsInPersian.keys())[:self.MAX_DESIRED_SELECTION]
        return desired_ones

    def crypto_description_row(self, name: str, symbol: str, price:float|int|str, short_text: bool=True):
        if isinstance(price, str):
            price = float(price)
        if symbol != 'USDT':
            rp_usd, rp_toman = self.rounded_prices(price, tether_as_unit_price=True)
        else:
            rp_usd, rp_toman = mathematix.cut_and_separate(price), mathematix.cut_and_separate(self.TetherInTomans)
        rp_toman = mathematix.persianify(rp_toman)
        return f'🔸 {CryptoCurrency.CoinsInPersian[symbol]}: {rp_toman} تومان / {rp_usd}$\n' if short_text \
            else f'🔸 {name} ({symbol}): {rp_usd}$\n{CryptoCurrency.CoinsInPersian[symbol]}: {rp_toman} تومان\n'



# --------- COINGECKO -----------
class CoinGecko(CryptoCurrency):
    '''CoinGecko Class. The object of this class will get the cryptocurrency prices from coingecko.'''
    def __init__(self, params=None) -> None:

        super(CoinGecko, self).__init__(url='https://api.coingecko.com/api/v3/coins/list', source="CoinGecko.com",
                                cache_file_name="coingecko.json")

    def extract_api_response(self, desired_coins=None, short_text=True,  optional_api_data:list = None):
        'Construct a text string consisting of each desired coin prices of a special user.'
        desired_coins = self.get_desired_ones(desired_coins)
        api_data = optional_api_data or self.latest_data
        res = ''
        for coin in api_data:
            symbol = coin['symbol'].upper()
            name = coin['name'] if symbol != self.TETHER_SYMBOLTETHER_SYMBOL else 'Tether'
            if symbol in desired_coins:
                price = coin['market_data']['current_price'][self.DOLLAR_SYMBOL.lower()]
                res += self.crypto_description_row(name, symbol, price)

        if res:
            res = f'📌 #قیمت_لحظه_ای #بازار_ارز_دیجیتال \n{res}'
        return res


# --------- COINMARKETCAP -----------
class CoinMarketCap(CryptoCurrency):
    '''CoinMarketCap Class. The object of this class will get the cryptocurrency prices from CoinMarketCap.'''

    def __init__(self, api_key, price_unit='USD', params=None) -> None:
        super(CoinMarketCap, self).__init__(
            url='https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest',
            source="CoinMarketCap.com", cache_file_name='coinmarketcap.json')
        self.api_key: str = api_key
        self.price_unit: str = price_unit
        self.symbols_list: str = None
        self.update_symbols_list()

    def update_symbols_list(self):
        '''Construct the list of all cryptocurrency coin symbols'''
        self.symbols_list = ''
        for cn in CryptoCurrency.CoinsInPersian:
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

    def extract_api_response(self, desired_coins:list = None, short_text:bool = True, optional_api_data:list = None):
        '''This function constructs a text string that in each row has the latest price of a
            cryptocurrency unit in two price units, dollars and Tomans'''
        desired_coins = self.get_desired_ones(desired_coins)
        api_data = optional_api_data or self.latest_data

        if not api_data:
            raise NoLatestDataException('Use for anouncing prices!')

        res = ''
        for coin in desired_coins:
            price = api_data[coin][0]['quote'][self.price_unit]['price']
            name = api_data[coin][0]['name'] if coin != BaseAPIManager.TETHER_SYMBOL else 'Tether'
            res += self.crypto_description_row(name, coin, price, short_text=short_text)

        if res:
            res = f'📌 #قیمت_لحظه_ای #بازار_ارز_دیجیتال \n{res}'
        return res


    def equalizer_row(self, unit_symbol: str, value: float|int):
        '''returns the row shape/format of the equalizing coin.'''
        value_cut = mathematix.cut_and_separate(value)
        value = mathematix.persianify(value_cut)
        return f'🔸 {value} {CryptoCurrency.CoinsInPersian[unit_symbol]}\n'

    def equalize(self, source_unit_symbol: str, amount: float|int, desired_coins: list = None) -> str:
        '''This function gets an amount param, alongside with a source_unit_symbol [and abviously with the users desired coins]
            and it returns a text string, that in each row of that, shows that amount equivalent in another cryptocurrency unit.'''
        # First check the required data is prepared
        if not self.latest_data:
            raise NoLatestDataException('Use for equalizing!')
        if source_unit_symbol not in self.latest_data or source_unit_symbol not in CryptoCurrency.CoinsInPersian:
            raise InvalidInputException('Coin symbol!')

        # text header
        res: str = f'💱☯ معادل سازی ♻️💱\nبا توجه به آخرین قیمت های بازار ارز دیجیتال ' + \
            ("%s %s" % (mathematix.persianify(amount), CryptoCurrency.CoinsInPersian[source_unit_symbol])) + ' معادل است با:\n\n'
        # first row is the equivalent price in USD(the price unit selected by the bot configs.)
        absolute_amount: float = amount * float(self.latest_data[source_unit_symbol][0]['quote'][self.price_unit]['price'])
        res += f'🔸 {mathematix.persianify(mathematix.cut_and_separate(absolute_amount))} {SourceArena.GetPersianName(BaseAPIManager.DOLLAR_SYMBOL)}\n'

        desired_coins = self.get_desired_ones(desired_coins)
        if BaseAPIManager.TETHER_SYMBOL not in desired_coins:
            desired_coins.insert(0, BaseAPIManager.TETHER_SYMBOL)
        for coin in desired_coins:
            amount_in_this_coin_unit = absolute_amount  / float(self.latest_data[coin][0]['quote'][self.price_unit]['price'])
            res += self.equalizer_row(coin, amount_in_this_coin_unit)

        return res
