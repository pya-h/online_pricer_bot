from tools import manuwriter, mathematix
from api.crypto import CoinGecko, CoinMarketCap
from api.currency import SourceArena
from db.vip_models import VIPAccount


class PostManager:
    '''This class wraps all necessary api managers and make them work together, and constructs posts.'''
    def __init__(self, source_arena_api_key: str, aban_tether_api_key:str, coinmarketcap_api_key: str) -> None:
        self.source_arena_api_key: str = source_arena_api_key
        self.aban_tether_api_key: str = aban_tether_api_key
        self.coinmarketcap_api_key: str = coinmarketcap_api_key

        self.cryptoManager: CoinGecko|CoinMarketCap = CoinMarketCap(self.coinmarketcap_api_key)  # api manager object: instance of CoinGecko or CoinMarketCap
        self.currencyManager: SourceArena = SourceArena(self.source_arena_api_key, self.aban_tether_api_key)

    def sign_post(self, post_body: str, interval: float, for_channel: bool=True) -> str:
        timestamp = mathematix.timestamp()
        interval_fa = mathematix.persianify(interval.__str__())
        header = f'✅ بروزرسانی قیمت ها (هر {interval_fa} دقیقه)\n' if for_channel else ''
        header += timestamp + '\n' # + '🆔 آدرس کانال: @Online_pricer\n⚜️ آدرس دیگر مجموعه های ما: @Crypto_AKSA\n'
        footer = '🆔 @Online_pricer\n🤖 @Online_pricer_bot'
        return f'{header}\n{post_body}\n{footer}'

    def create_post(self, desired_coins:list = None, desired_currencies:list = None, exactly_right_now: bool=True, short_text: bool=True, for_channel: bool=True) -> str:
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



class VIPPostManager(PostManager):
    '''Extended version of PostManager, this class contains all the post jobs, constructs posts and manages channel post and updates'''
    def __init__(self, source_arena_api_key: str, aban_tether_api_key:str, coinmarketcap_api_key: str, bot_username: str = None) -> None:
        super().__init__(source_arena_api_key, aban_tether_api_key, coinmarketcap_api_key)
        self.bot_username = bot_username

    def create_post(self, account: VIPAccount, channel_link: str = None, short_text: bool=True) -> str:
        currencies = cryptos = ''

        try:
            if account.desired_currencies or (not account.desired_coins and not account.desired_currencies):
                # this condition is for preventing default values, when user has selected just cryptos
                currencies = self.currencyManager.get_desired_cache(account.desired_currencies)
        except Exception as ex:
            manuwriter.log("Cannot obtain Currencies! ", ex, self.currencyManager.Source)
            # TODO: What to do here?
        try:
            if account.desired_coins or (not account.desired_coins and not account.desired_currencies):
                # this condition is for preventing default values, when user has selected just currencies
                cryptos = self.cryptoManager.get_desired_cache(account.desired_coins, short_text)
        except Exception as ex:
            manuwriter.log("Cannot obtain Cryptos! ", ex, self.cryptoManager.Source)
            # TODO: What to do here?
        return self.sign_post(currencies + cryptos, channel_link=channel_link)


    def sign_post(self, message: str, interval: float, channel_link: str) -> str:
        post_text = super().sign_post(message, interval, for_channel=True)

        if self.bot_username:
            post_text += f'\n🤖 @{self.bot_username}'
        if channel_link:
            post_text += f'\n🆔 @{channel_link}'
        return post_text

    def update_latest_data(self):
        '''This will be called by vip robot as a job on a propper interval, so that channels use the most recent data gradually, alongside considering performance handling issues.'''
        try:
            self.currencyManager.load_cache()
        except:
            # force reload
            try:
                manuwriter.log('Currency cache load failed. Trying force reload (API call) to update channels currency latest_data!', ex, 'VIP_CACHE')
                self.currencyManager.latest_data = self.currencyManager.send_request()
            except Exception as ex:
                manuwriter.log('Can not update currency data for other channels use!', ex, 'VIP_FATALITY')

        try:
            self.cryptoManager.load_cache()
        except:
            # force reload
            try:
                manuwriter.log('Crypto cache load failed. Using force reload (API call) to update channels crypto latest_data!', ex, 'VIP_CACHE')
                self.cryptoManager.latest_data = self.cryptoManager.send_request()
            except:
                manuwriter.log('Can not update crypto data for other channels use!', ex, 'VIP_FATALITY')
