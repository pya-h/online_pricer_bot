import coinmarketcapapi as cmc_api
from api.base import *
from tools.exceptions import NoLatestDataException, InvalidInputException
from typing import Union, List


# Parent Class
class CryptoCurrencyService(APIService):
    CoinsInPersian: Dict[str, str] | None = None

    @staticmethod
    def Find(words: List[str], index: int, word_count: int, max_name_word_count=4):
        # word_count is for not calculating the words length everytime.
        word = words[i]
        multi_word_findings: Dict[str, str] = []
        for coin in CryptoCurrencyService.CoinsInPersian:
            if coin == word or CryptoCurrencyService.CoinsInPersian[coin] == word:
                return coin
            coin_words = CryptoCurrencyService.CoinsInPersian[coin].split()
            coin_cord_count = len(coin_words)

            if word in CryptoCurrencyService.CoinsInPersian[coin]:
                # for multi-word coins
                i = index + max_name_word_count if index + max_name_word_count < word_count else word_count - 1
        return None

    @staticmethod
    def LoadPersianNames() -> dict:
        coins_fa = "{}"
        try:
            persian_coin_names_file = open("./api/data/coins.fa.json", "r")
            coins_fa = persian_coin_names_file.read()
            persian_coin_names_file.close()
        except:
            pass
        return json.loads(coins_fa)

    def __init__(self, url: str, source: str, max_desired_selection: int = 5, params=None, cache_file_name: str = None) -> None:
        super().__init__(url, source, max_desired_selection, params, cache_file_name)
        if not CryptoCurrencyService.CoinsInPersian:
            CryptoCurrencyService.CoinsInPersian = CryptoCurrencyService.LoadPersianNames()
        self.get_desired_ones = (
            lambda desired_ones: desired_ones or list(CryptoCurrencyService.CoinsInPersian.keys())[: self.max_desired_selection]
        )

    @staticmethod
    def GetPersianName(symbol: str) -> str:
        if not CryptoCurrencyService.CoinsInPersian:
            CryptoCurrencyService.LoadPersianNames()
        if symbol not in CryptoCurrencyService.CoinsInPersian:
            raise InvalidInputException("Crypto symbol!")
        return CryptoCurrencyService.CoinsInPersian[symbol]


# --------- COINGECKO -----------
class CoinGeckoService(CryptoCurrencyService):
    """CoinGecko Class. The object of this class will get the cryptocurrency prices from coingecko."""

    def __init__(self, params=None) -> None:

        super(CoinGeckoService, self).__init__(
            url="https://api.coingecko.com/api/v3/coins/list", source="CoinGecko.com", cache_file_name="coingecko.json"
        )

    def extract_api_response(self, desired_coins=None, short_text=True, optional_api_data: list | None = None):
        "Construct a text string consisting of each desired coin prices of a special user."
        desired_coins: List[str] = self.get_desired_ones(desired_coins)
        api_data = optional_api_data or self.latest_data
        res = ""
        for coin in api_data:
            symbol = coin["symbol"].upper()
            name = coin["name"] if symbol != self.TETHER_SYMBOL else "Tether"
            if symbol in desired_coins:
                price = coin["market_data"]["current_price"][self.DOLLAR_SYMBOL.lower()]
                res += self.get_price_description_row(name, symbol, price)

        if res:
            res = f"📌 #قیمت_لحظه_ای #بازار_ارز_دیجیتال \n{res}"
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

    @staticmethod
    def ListToDict(source_list: list, key_as: str = "symbol"):
        result = {}

        for item in source_list:
            try:
                symbol = item[key_as].upper()
                if symbol in CoinMarketCapService.CoinsInPersian and symbol not in result:
                    result[symbol] = item
            except:
                pass
        return result

    async def get_request(self):
        """Send request to coinmarketcap to receive the prices. This function differs from other .get_request methods from other BaseAPIService childs"""
        latest_cap = None
        result: dict = {}
        try:
            latest_cap = self.cmc_api.cryptocurrency_listings_latest(limit=5000)
            if latest_cap and latest_cap.data:
                result = self.ListToDict(latest_cap.data)
            self.cache_data(json.dumps(result))
        except Exception as ex:
            manuwriter.log("CoinMarketCap Api Failure", exception=ex, category_name="CoinMarketCapFailure")
        return result

    def extract_api_response(self, desired_coins: list = None, short_text: bool = True, optional_api_data: list = None):
        """This function constructs a text string that in each row has the latest price of a
        cryptocurrency unit in two price units, dollars and Tomans"""
        desired_coins = self.get_desired_ones(desired_coins)
        api_data = optional_api_data or self.latest_data

        if not api_data:
            raise NoLatestDataException("Use for announcing prices!")

        res = ""
        for coin in desired_coins:
            symbol = coin.upper()
            if symbol in api_data:
                row = self.get_price_description_row(symbol, api_data, short_text=short_text)
                res += row if row else f"❗️ {CryptoCurrencyService.CoinsInPersian[coin]}: قیمت دریافت نشد."

        if res:
            res = f"📌 #قیمت_لحظه_ای #بازار_ارز_دیجیتال \n{res}"
        return res

    def usd_to_cryptos(self, absolute_amount: float | int, source_unit_symbol: str, cryptos: list = None) -> str:
        cryptos = self.get_desired_ones(cryptos)
        res: str = ""

        for coin in cryptos:
            if coin == source_unit_symbol:
                continue
            coin_equalized_price = absolute_amount / float(self.latest_data[coin]["quote"][self.price_unit]["price"])
            coin_equalized_price = mathematix.persianify(mathematix.cut_and_separate(coin_equalized_price))
            res += f"🔸 {coin_equalized_price} {CryptoCurrencyService.CoinsInPersian[coin]}\n"

        return f"📌#بازار_ارز_دیجیتال\n{res}"

    def equalize(
        self, source_unit_symbol: str, amount: float | int, desired_cryptos: list = None
    ) -> Union[str, float | int, float | int]:
        """This function gets an amount param, alongside with a source_unit_symbol [and abviously with the users desired coins]
        and it returns a text string, that in each row of that, shows that amount equivalent in another cryptocurrency unit."""
        # First check the required data is prepared
        if not self.latest_data:
            raise NoLatestDataException("use for equalizing!")
        if source_unit_symbol not in self.latest_data or source_unit_symbol not in CryptoCurrencyService.CoinsInPersian:
            raise InvalidInputException("Coin symbol!")

        # text header
        header: str = (
            "✅ %s %s" % (mathematix.persianify(amount), CryptoCurrencyService.CoinsInPersian[source_unit_symbol])
        ) + " معادل است با:\n\n"

        # first row is the equivalent price in USD(the price unit selected by the bot configs.)
        try:
            absolute_amount: float = amount * float(self.latest_data[source_unit_symbol]["quote"][self.price_unit]["price"])
        except:
            raise ValueError(f"{source_unit_symbol} has not been received from the API.")

        return (
            header,
            self.usd_to_cryptos(absolute_amount, source_unit_symbol, desired_cryptos),
            absolute_amount,
            self.to_irt_exact(absolute_amount, True),
        )

    def get_single_price(self, crypto_symbol: str, price_unit: str = "usd", tether_instead_of_dollars: bool = True):
        if not self.latest_data or not isinstance(self.latest_data, dict):
            return None
        coin = crypto_symbol.upper()
        price_unit = price_unit.lower()
        if coin == self.TETHER_SYMBOL and price_unit == "irt":
            return self.TetherInTomans

        data = self.latest_data[coin] if coin in self.latest_data else None

        if not data:
            return None

        return (
            self.to_irt_exact(data["quote"][self.price_unit]["price"], tether_instead_of_dollars)
            if price_unit == "irt"
            else data["quote"][self.price_unit]["price"]
        )

    def get_price_description_row(self, symbol: str, source_data: Dict[str, any] | None = None, short_text: bool = True) -> str:
        api_data = source_data if source_data else self.latest_data
        price: float
        name: str
        try:
            price = api_data[symbol]["quote"][self.price_unit]["price"]
            name = api_data[symbol]["name"] if symbol != BaseAPIService.TETHER_SYMBOL else "Tether"
        except:
            return None

        if isinstance(price, str):
            price = float(price)

        if symbol != "USDT":
            rp_usd, rp_toman = self.rounded_prices(price, tether_as_unit_price=True)
        else:
            rp_usd, rp_toman = mathematix.cut_and_separate(price), mathematix.cut_and_separate(self.TetherInTomans)

        rp_toman = mathematix.persianify(rp_toman)

        return (
            f"🔸 {CryptoCurrencyService.CoinsInPersian[symbol]}: {rp_toman} تومان / {rp_usd}$\n"
            if short_text
            else f"🔸 {name} ({symbol}): {rp_usd}$\n{CryptoCurrencyService.CoinsInPersian[symbol]}: {rp_toman} تومان\n"
        )
