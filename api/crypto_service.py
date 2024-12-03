import coinmarketcapapi as cmc_api
from api.base import *
from tools.exceptions import NoLatestDataException, InvalidInputException
from typing import Union, List


# Parent Class
class CryptoCurrencyService(APIService):
    coinsInPersian: Dict[str, str] | None = None
    defaults = ("BTC", "ETH", "USDT", "BNB", "SOL")
    userDefaults = ("BTC", "USDT")

    def __init__(self, url: str, source: str, params=None, cache_file_name: str = None) -> None:
        super().__init__(url, source, params, cache_file_name)
        if not CryptoCurrencyService.coinsInPersian:
            CryptoCurrencyService.coinsInPersian = CryptoCurrencyService.loadPersianNames()

    @staticmethod
    def getDefaultCryptos():
        return list(CryptoCurrencyService.defaults)

    @staticmethod
    def getUserDefaultCryptos():
        return list(CryptoCurrencyService.userDefaults)

    def get_desired_ones(self, desired_ones: List[str] | None):
        return desired_ones or list(CryptoCurrencyService.defaults)

    @staticmethod
    def find(words: List[str], index: int, word_count: int, max_name_word_count=4):
        # word_count is for not calculating the words length every time.
        word = words[i]
        for coin in CryptoCurrencyService.coinsInPersian:
            if coin == word or CryptoCurrencyService.coinsInPersian[coin] == word:
                return coin
            coin_words = CryptoCurrencyService.coinsInPersian[coin].split()
            if word in CryptoCurrencyService.coinsInPersian[coin]:
                # for multi-word coins
                i = index + max_name_word_count if index + max_name_word_count < word_count else word_count - 1
        return None

    @staticmethod
    def loadPersianNames() -> dict:
        coins_fa = "{}"
        try:
            persian_coin_names_file = open("./api/data/coins.fa.json", "r")
            coins_fa = persian_coin_names_file.read()
            persian_coin_names_file.close()
        except:
            pass
        return json.loads(coins_fa)

    @staticmethod
    def getPersianName(symbol: str) -> str:
        if not CryptoCurrencyService.coinsInPersian:
            CryptoCurrencyService.loadPersianNames()
        if symbol not in CryptoCurrencyService.coinsInPersian:
            raise InvalidInputException("Crypto symbol!")
        return CryptoCurrencyService.coinsInPersian[symbol]


# --------- COINGECKO -----------
class CoinGeckoService(CryptoCurrencyService):
    """CoinGecko Class. The object of this class will get the cryptocurrency prices from coingecko."""

    def __init__(self, params=None) -> None:

        super(CoinGeckoService, self).__init__(
            url="https://api.coingecko.com/api/v3/coins/list", source="CoinGecko.com", cache_file_name="coingecko.json"
        )

    def get_price_description_row(self, symbol: str, language: str = 'fa', no_price_message: str | None = None) -> str:
        pass

    def extract_api_response(self, desired_coins: List[str] | None = None, language: str = 'fa', no_price_message: str | None = None):
        "Construct a text string consisting of each desired coin prices of a special user."
        desired_coins: List[str] = self.get_desired_ones(desired_coins)
        res = ""
        for symbol in desired_coins:   
            res += self.get_price_description_row(symbol.upper(), language, no_price_message)

        return res

    # TODO: Implement equalize for CoinGecko too


# --------- COINMARKETCAP -----------
class CoinMarketCapService(CryptoCurrencyService):
    """CoinMarketCap Class. The object of this class will get the cryptocurrency prices from CoinMarketCap."""

    def __init__(self, api_key, price_unit="USD", params=None) -> None:
        super(CoinMarketCapService, self).__init__(
            url="https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            source="CoinMarketCap.com",
            cache_file_name="coinmarketcap.json",
        )
        self.api_key: str = api_key
        self.price_unit: str = price_unit
        self.cmc_api = cmc_api.CoinMarketCapAPI(self.api_key)

    def set_price_unit(self, pu):
        self.price_unit = pu

    def raw_data_to_price_dict(self, source_list: list, key_as: str = "symbol"):
        result = {}

        for item in source_list:
            try:
                symbol = item[key_as].upper()
                if symbol in CoinMarketCapService.coinsInPersian and symbol not in result:
                    result[symbol] = item["quote"][self.price_unit]
            except:
                pass
        return result

    async def get_request(self):
        """Send request to coinmarketcap to receive the prices. This function differs from other .get_request methods from other BaseAPIService children"""
        latest_cap = None
        result: dict = {}
        try:
            latest_cap = self.cmc_api.cryptocurrency_listings_latest(limit=5000)
            if latest_cap and latest_cap.data:
                result = self.raw_data_to_price_dict(latest_cap.data)
            self.cache_data(json.dumps(result))
        except Exception as ex:
            manuwriter.log("CoinMarketCap Api Failure", exception=ex, category_name="CoinMarketCapFailure")
        return result

    def extract_api_response(self, desired_coins: List[str] = None, language: str = 'fa', no_price_message: str | None = None):
        """This function constructs a text string that in each row has the latest price of a
        cryptocurrency unit in two price units, dollars and Tomans"""
        desired_coins = self.get_desired_ones(desired_coins)
        if not self.latest_data:
            raise NoLatestDataException("Use for announcing prices!")
        res = ""
        for coin in desired_coins:
            res += self.get_price_description_row(coin.upper(), language, no_price_message)
        return res

    def usd_to_cryptos(self, absolute_amount: float | int, source_unit_symbol: str, cryptos: List[str] | None = None, language: str = 'fa') -> str:
        cryptos = self.get_desired_ones(cryptos)
        res: str = ""
        coin_equalized_price: str
        for coin in cryptos:
            if coin == source_unit_symbol:
                continue
            try:
                coin_equalized_price = absolute_amount / float(self.latest_data[coin]["price"])
                coin_equalized_price = mathematix.cut_and_separate(coin_equalized_price)
            except Exception as x:
                manuwriter.log('No Price Data:', x, 'PriceData')
                coin_equalized_price = '?'
            if language != 'fa':
                res += f"🔸 {coin_equalized_price} {coin}\n"
            else:
                res += f"🔸 {mathematix.persianify(coin_equalized_price)} {CryptoCurrencyService.coinsInPersian[coin]}\n"
        return res

    def equalize(
        self, source_unit_symbol: str, amount: float | int, desired_cryptos: List[str] | None = None, language: str = 'fa'
    ) -> Union[str, float | int, float | int]:
        """This function gets an amount param, alongside with a source_unit_symbol [and obviously with the users desired coins]
        and it returns a text string, that in each row of that, shows that amount equivalent in another cryptocurrency unit."""
        # First check the required data is prepared
        if not self.latest_data:
            raise NoLatestDataException("use for equalizing!")
        if source_unit_symbol not in self.latest_data or source_unit_symbol not in CryptoCurrencyService.coinsInPersian:
            raise InvalidInputException("Coin symbol!")

        # first row is the equivalent price in USD(the price unit selected by the bot configs.)
        try:
            absolute_amount: float = amount * float(self.latest_data[source_unit_symbol]["price"])
        except:
            raise ValueError(f"{source_unit_symbol} has not been received from the API.")

        return (
            self.usd_to_cryptos(absolute_amount, source_unit_symbol, desired_cryptos, language) if desired_cryptos else None,
            absolute_amount,
            self.to_irt_exact(absolute_amount, True)
        )

    def get_single_price(self, crypto_symbol: str, price_unit: str = "usd", tether_instead_of_dollars: bool = True):
        if not isinstance(self.latest_data, dict):
            return None
        coin = crypto_symbol.upper()
        price_unit = price_unit.lower()
        if coin == self.tetherSymbol and price_unit == "irt":
            return self.tetherInTomans

        if coin not in self.latest_data:
            return None

        data = self.latest_data[coin]

        if "price" not in data:
            return None

        return (
            self.to_irt_exact(data["price"], tether_instead_of_dollars)
            if price_unit == "irt"
            else data["price"]
        )

    def get_price_description_row(self, symbol: str, language: str = 'fa', no_price_message: str | None = None) -> str:
        try:
            price: float
            price = self.latest_data[symbol]["price"]

            if isinstance(price, str):
                price = float(price)

            if symbol != "USDT":
                rp_usd, rp_toman = self.rounded_prices(price, tether_as_unit_price=True)
            else:
                rp_usd, rp_toman = mathematix.cut_and_separate(price), mathematix.cut_and_separate(self.tetherInTomans)

            if language != 'fa':
                return f"🔸 {symbol}: {rp_toman} {self.tomanSymbol} / {rp_usd}$\n"
            rp_toman = mathematix.persianify(rp_toman)
            return f"🔸 {CryptoCurrencyService.coinsInPersian[symbol]}: {rp_toman} تومان / {rp_usd}$\n"
        except:
            pass
        return f"{CryptoCurrencyService.coinsInPersian[symbol]}: " + (no_price_message or "❗️") + "\n"
