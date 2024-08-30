from tools.mathematix import timestamp, persianify
from tools.manuwriter import log
from api.crypto_service import CoinGeckoService, CoinMarketCapService
from api.currency_service import NavasanService
from models.group import Group
from models.channel import Channel
from bot.types import ResourceManager


class PostMan:
    """This class wraps all necessary api services and make them work together, and constructs posts."""

    def __init__(
        self,
        resourceman: ResourceManager,
        source_arena_api_key: str,
        coinmarketcap_api_key: str,
        nobitex_api_token: str,
        aban_tether_api_token: str | None = None,
    ) -> None:
        self.resourceman = resourceman
        self.source_arena_api_key: str = source_arena_api_key
        self.nobitex_api_token: str = nobitex_api_token
        self.aban_tether_api_token: str = aban_tether_api_token

        self.coinmarketcap_api_key: str = coinmarketcap_api_key

        self.crypto_service: CoinGeckoService | CoinMarketCapService = CoinMarketCapService(
            self.coinmarketcap_api_key
        )  # api service object: instance of CoinGecko or CoinMarketCap
        self.currency_service: NavasanService = NavasanService(self.source_arena_api_key, self.nobitex_api_token)

    def arrange_post_sections(
        self, fiat_body: str, gold_body: str, crypto_body: str, channel_interval: float | None = None, language: str = "fa"
    ) -> str:
        post: str = ""
        if channel_interval:
            channel_interval = str(int(channel_interval)) if language != 'fa' else persianify(channel_interval.__str__()) 
            post = self.resourceman.text('announcement_post_interval', language) % (channel_interval, )
        post += timestamp(language)
        if fiat_body:
            tags_fiat = self.resourceman.text('announcement_fiat_header', language)
            post += f"\n\n{tags_fiat}\n{fiat_body}"
        if gold_body:
            tags_gold = self.resourceman.text('announcement_gold_header', language)
            post += f"\n\n{tags_gold}\n{gold_body}"
        if crypto_body:
            tags_crypto = self.resourceman.text('announcement_crypto_header', language)
            post += f"\n\n{tags_crypto}\n{crypto_body}"
        return f"{post}\n\n🆔 @Online_pricer\n🤖 @Online_pricer_bot"

    async def create_post(
        self,
        desired_coins: list = None,
        desired_currencies: list = None,
        get_most_recent_price: bool = True,
        channel_interval: float | None = None,
        language: str = "fa",
    ) -> str:
        fiat = gold = cryptos = ""

        try:
            if desired_currencies or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just cryptos
                fiat, gold = (
                    await self.currency_service.get(desired_currencies)
                    if get_most_recent_price
                    else self.currency_service.get_latest(desired_currencies)
                )
        except Exception as ex:
            log("Cannot obtain Currencies! ", ex, self.currency_service.Source)
            fiat, gold = self.currency_service.get_latest(desired_currencies)
        try:
            if desired_coins or (not desired_coins and not desired_currencies):
                # this condition is for preventing default values, when user has selected just currencies
                cryptos = (
                    await self.crypto_service.get(desired_coins)
                    if get_most_recent_price
                    else self.crypto_service.get_latest(desired_coins)
                )
        except Exception as ex:
            log("Cannot obtain Cryptos! ", ex, self.crypto_service.Source)
            cryptos = self.crypto_service.get_latest(desired_coins)
        return self.arrange_post_sections(fiat, gold, cryptos, channel_interval=channel_interval, language=language)


    def create_channel_post(self, channel: Channel):
        fiat = gold = crypto = ''
        try:
            fiat, gold = self.currency_service.get_latest(channel.selected_currencies)
        except:
            pass
        try:
            crypto = self.crypto_service.get_latest(channel.selected_coins)
        except:
            pass

        post = ''
        tags_fiat = tags_gold = tags_crypto = ''
        if channel.message_show_market_tags:
            tags_fiat = self.resourceman.text('announcement_fiat_header', channel.language) + "\n"
            tags_gold = self.resourceman.text('announcement_gold_header', channel.language) + "\n"
            tags_crypto = self.resourceman.text('announcement_crypto_header', channel.language) + "\n"

        if fiat:
            post += f"{tags_fiat}{fiat}"
        if gold:
            post += f"{'\n\n' if post else ''}{tags_gold}{gold}"
        if crypto:
            post += f"{'\n\n' if post else ''}{tags_crypto}{crypto}"

        return PostMan.customizePost(post, channel, channel.language)

    @staticmethod
    def customizePost(post_body: str, community: Group | Channel, language: str = "fa"):
        if community.message_header:
            post_body = f"{community.message_header}\n\n{post_body}"
        if community.message_footnote:
            post_body += f"\n\n{community.message_footnote}"
        if community.message_show_date_tag:
            return timestamp(language) + f"\n{post_body}"
        return post_body
        