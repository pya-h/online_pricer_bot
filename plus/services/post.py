from plus.models.account import AccountPlus
from plus.models.channel import Channel
from services.post import PostService
from tools import manuwriter


class PostServicePlus(PostService):
    '''Extended version of PostService, this class contains all the post jobs, constructs posts and manages channel post and updates'''
    def __init__(self, source_arena_api_key: str, aban_tether_api_key:str, coinmarketcap_api_key: str, bot_username: str = None) -> None:
        super().__init__(source_arena_api_key, aban_tether_api_key, coinmarketcap_api_key)
        self.bot_username = bot_username

    def create_post(self, account: AccountPlus, channel: Channel = None, short_text: bool=True) -> str:
        currencies = cryptos = ''

        try:
            if account.desired_currencies or (not account.desired_coins and not account.desired_currencies):
                # this condition is for preventing default values, when user has selected just cryptos
                currencies = self.currency_service.get_desired_cache(account.desired_currencies)
        except Exception as ex:
            manuwriter.log("Cannot obtain Currencies! ", ex, self.currency_service.Source)
            # TODO: What to do here?
        try:
            if account.desired_coins or (not account.desired_coins and not account.desired_currencies):
                # this condition is for preventing default values, when user has selected just currencies
                cryptos = self.crypto_service.get_desired_cache(account.desired_coins, short_text)
        except Exception as ex:
            manuwriter.log("Cannot obtain Cryptos! ", ex, self.crypto_service.Source)
            # TODO: What to do here?
        return self.sign_post(currencies + cryptos, channel=channel)


    def sign_post(self, message: str, channel: Channel) -> str:
        post_text = super().sign_post(message, channel.interval, for_channel=True)

        if self.bot_username:
            post_text += f'\n🤖 @{self.bot_username}'
        if channel and channel.name:
            post_text += f'\n🆔 @{channel.name}'
        return post_text

    def update_latest_data(self):
        '''This will be called by plus robot as a job on a propper interval, so that channels use the most recent data gradually, alongside considering performance handling issues.'''
        try:
            self.currency_service.load_cache()
        except Exception as ex:
            # force reload
            try:
                manuwriter.log('Currency cache load failed. Trying force reload (API call) to update channels currency latest_data!', ex, 'PLUS_CACHE')
                self.currency_service.latest_data = self.currency_service.get_request()
            except Exception as ex:
                manuwriter.log('Can not update currency data for other channels use!', ex, 'PLUS_FATALITY')

        try:
            self.crypto_service.load_cache()
        except Exception as ex:
            # force reload
            try:
                manuwriter.log('Crypto cache load failed. Using force reload (API call) to update channels crypto latest_data!', ex, 'PLUS_CACHE')
                self.crypto_service.latest_data = self.crypto_service.get_request()
            except Exception as ex:
                manuwriter.log('Can not update crypto data for other channels use!', ex, 'PLUS_FATALITY')
        print('Updated post_service')
