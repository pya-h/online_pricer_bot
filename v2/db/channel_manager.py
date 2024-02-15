from typing import Callable
from payagraph.job import ParallelJob
from typing import Callable, Dict
from db.vip_models import Channel, Account
from tools import manuwriter, mathematix
from api.crypto import CoinGecko, CoinMarketCap
from api.currency import SourceArena


class PostJob(ParallelJob):

    def __init__(self, channel: Channel, interval: int, function: Callable[..., any], *params) -> None:
        super().__init__(interval, function, *params)
        self.channel: Channel = channel
        self.account: Account = Account.Get(channel.owner_id)

    def post(self):
        pass



class PostManager:
    '''This class wraps all necessary api managers and make them work together, and constructs posts.'''
    def __init__(self, source_arena_api_key: str, aban_tether_api_key:str, coinmarketcap_api_key: str) -> None:
        self.source_arena_api_key: str = source_arena_api_key
        self.aban_tether_api_key: str = aban_tether_api_key
        self.coinmarketcap_api_key: str = coinmarketcap_api_key

        self.cryptoManager: CoinGecko|CoinMarketCap = CoinMarketCap(self.coinmarketcap_api_key)  # api manager object: instance of CoinGecko or CoinMarketCap
        self.currencyManager: SourceArena = SourceArena(self.source_arena_api_key, self.aban_tether_api_key)

    def sign_post(self, message: str, interval: float, for_channel: bool=True) -> str:
        timestamp = mathematix.timestamp()
        interval_fa = mathematix.persianify(interval.__str__())
        header = f'✅ بروزرسانی قیمت ها (هر {interval_fa} دقیقه)\n' if for_channel else ''
        header += timestamp + '\n' # + '🆔 آدرس کانال: @Online_pricer\n⚜️ آدرس دیگر مجموعه های ما: @Crypto_AKSA\n'
        footer = '🆔 @Online_pricer\n🤖 @Online_pricer_bot'
        return f'{header}\n{message}\n{footer}'

    def construct_new_post(self, desired_coins=None, desired_currencies=None, exactly_right_now=True, short_text=True, for_channel=True) -> str:
        currencies = cryptos = ''

        try:
            if desired_currencies or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just cryptos
                currencies = self.currencyManager.get(desired_currencies, short_text=short_text) if exactly_right_now else \
                    self.currencyManager.get_latest(desired_currencies)
        except Exception as ex:
            manuwriter.log("Cannot obtain Currencies! ", ex, self.currencyManager.Source)
            currencies = self.currencyManager.get_latest(desired_currencies, short_text=short_text)
        try:
            if desired_coins or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just currencies
                cryptos = self.cryptoManager.get(desired_coins, short_text=short_text) if exactly_right_now else \
                    self.cryptoManager.get_latest(desired_coins, short_text)
        except Exception as ex:
            manuwriter.log("Cannot obtain Cryptos! ", ex, self.cryptoManager.Source)
            cryptos = self.cryptoManager.get_latest(desired_coins, short_text=short_text)
        return self.sign_post(currencies + cryptos, for_channel=for_channel)                                            



class ChannelPostManager(PostManager):
    '''Extended version of PostManager, this class contains all the post jobs, constructs posts and manages channel post and updates'''
    def __init__(self, source_arena_api_key: str, aban_tether_api_key:str, coinmarketcap_api_key: str) -> None:
        self.source_arena_api_key: str = source_arena_api_key
        self.aban_tether_api_key: str = aban_tether_api_key
        self.coinmarketcap_api_key: str = coinmarketcap_api_key

        self.cryptoManager: CoinGecko|CoinMarketCap = CoinMarketCap(self.coinmarketcap_api_key)  # api manager object: instance of CoinGecko or CoinMarketCap
        self.currencyManager: SourceArena = SourceArena(self.source_arena_api_key, self.aban_tether_api_key)
        self.post_jobs: Dict[PostJob] = dict()


    def construct_new_post(self, desired_coins=None, desired_currencies=None, exactly_right_now=True, short_text=True, for_channel=True) -> str:
        currencies = cryptos = ''

        try:
            if desired_currencies or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just cryptos
                currencies = self.currencyManager.get(desired_currencies, short_text=short_text) if exactly_right_now else \
                    self.currencyManager.get_cached_data(desired_currencies)
        except Exception as ex:
            manuwriter.log("Cannot obtain Currencies! ", ex, self.currencyManager.Source)
            currencies = self.currencyManager.get_cached_data(desired_currencies, short_text=short_text)
        try:
            if desired_coins or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just currencies
                cryptos = self.cryptoManager.get(desired_coins, short_text=short_text) if exactly_right_now else \
                    self.cryptoManager.get_cached_data(desired_coins, short_text)
        except Exception as ex:
            manuwriter.log("Cannot obtain Cryptos! ", ex, self.cryptoManager.Source)
            cryptos = self.cryptoManager.get_cached_data(desired_coins, short_text=short_text)
        return self.sign_post(currencies + cryptos, for_channel=for_channel)