from tools.mathematix import timestamp, persianify
from tools.manuwriter import log
from api.crypto_service import CoinGecko, CoinMarketCap
from api.currency_service import SourceArena


class PostMan:
    '''This class wraps all necessary api services and make them work together, and constructs posts.'''
    def __init__(self, source_arena_api_key: str, aban_tether_api_key:str, coinmarketcap_api_key: str) -> None:
        self.source_arena_api_key: str = source_arena_api_key
        self.aban_tether_api_key: str = aban_tether_api_key
        self.coinmarketcap_api_key: str = coinmarketcap_api_key

        self.crypto_service: CoinGecko|CoinMarketCap = CoinMarketCap(self.coinmarketcap_api_key)  # api service object: instance of CoinGecko or CoinMarketCap
        self.currency_service: SourceArena = SourceArena(self.source_arena_api_key, self.aban_tether_api_key)


    def sign_post(self, post_body: str, interval: float, for_channel: bool=True) -> str:
        interval_fa = persianify(interval.__str__())
        header = f'✅ بروزرسانی قیمت ها (هر {interval_fa} دقیقه)\n' if for_channel else ''
        header += timestamp() + '\n'
        footer = '🆔 @Online_pricer\n🤖 @Online_pricer_bot'
        return f'{header}\n{post_body}\n{footer}'

    async def create_post(self, desired_coins:list = None,
                          desired_currencies:list = None, exactly_right_now: bool=True, 
                          short_text: bool=True, for_channel: bool=True, interval: float = 10) -> str:
        currencies = cryptos = ''
        print(exactly_right_now)
        try:
            if desired_currencies or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just cryptos
                currencies = await self.currency_service.get(desired_currencies, short_text=short_text) if exactly_right_now else \
                    self.currency_service.get_latest(desired_currencies)
        except Exception as ex:
            log("Cannot obtain Currencies! ", ex, self.currency_service.Source)
            currencies = self.currency_service.get_latest(desired_currencies, short_text=short_text)
        try:
            if desired_coins or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just currencies
                cryptos = await self.crypto_service.get(desired_coins, short_text=short_text) if exactly_right_now else \
                    self.crypto_service.get_latest(desired_coins, short_text)
        except Exception as ex:
            log("Cannot obtain Cryptos! ", ex, self.crypto_service.Source)
            cryptos = self.crypto_service.get_latest(desired_coins, short_text=short_text)
        return self.sign_post(currencies + cryptos, for_channel=for_channel, interval=interval)