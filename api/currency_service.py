from api.base import *
import json
from tools.exceptions import InvalidInputException
from api.tether_service import AbanTetherService, NobitexService
from tools.manuwriter import log
from tools.mathematix import persianify
from tools.exceptions import NoLatestDataException
from typing import Union


def get_gold_names(filename: str):
    gold_names_fa = "{}"
    try:
        json_file = open(f"./api/data/{filename}.json", "r")
        gold_names_fa = json_file.read()
        json_file.close()
    except Exception as e:
        log('Cannot get currency names', exception=e, category_name='Currency')
    return json.loads(gold_names_fa)


def get_persian_currency_names():
    currency_names_fa = "{}"
    gold_names_fa = "{}"
    try:
        json_file = open("./api/data/national-currencies.fa.json", "r")
        currency_names_fa = json_file.read()
        json_file.close()
        json_file = open("./api/data/golds.fa.json", "r")
        gold_names_fa = json_file.read()
        json_file.close()
    except Exception as e:
        log('Cannot get currency names', exception=e, category_name='Currency')

    return json.loads(currency_names_fa), json.loads(gold_names_fa)


class CurrencyService(APIService):
    DefaultTetherInTomans = 61300
    DefaultUsbInTomans = 61000

    def __init__(self, url: str, source: str, cache_file_name: str, token: str, tether_service_token: str) -> None:
        super(CurrencyService, self).__init__(url=url, source=source, cache_file_name=cache_file_name)
        self.token = token
        self.tether_service_token = tether_service_token
        
        if not self.UsdInTomans:
            self.UsdInTomans = self.DefaultUsbInTomans
        if not self.TetherInTomans:
            self.TetherInTomans = self.DefaultTetherInTomans

class GoldService(BaseAPIService):
    EntitiesInDollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
    GoldsInPersian = None

    def __init__(self, token: str) -> None:
        super().__init__(url=f"https://sourcearena.ir/api/?token={token}&currency",
                         source="GoldService.ir", cache_file_name='SourceArenaGolds.json',)
        self.token = token
        if not GoldService.GoldsInPersian:
            GoldService.GoldsInPersian = get_gold_names('golds.sa.fa')

    async def append_gold_prices(self, api_data: dict):
        self.latest_data = await self.get_request()  # update latest
        for curr in self.latest_data:
            slug = curr['slug'].upper()

            if slug in GoldService.GoldsInPersian:
                # repetitive code OR using multiple conditions (?)
                if slug not in GoldService.EntitiesInDollars:
                    api_data[slug.lower()] = {'value': float(curr['price']) / 10,}
                else:
                    api_data[slug.lower()] = {'value': float(curr['price']), 'usd': True}

    # --------- Currency -----------
    async def get_request(self):
        response = await super(GoldService, self).get_request()
        return response["data"] if 'data' in response else []

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(GoldService, self).load_cache()['data']
        except:
            self.latest_data = []
        return self.latest_data


class NavasanService(CurrencyService):
    Defaults = ("USD", "EUR", "AED", "GBP", "TRY", 'ONS', 'TALA_18', 'TALA_MESGHAL', 'SEKE_EMAMI', 'SEKE_GERAMI',)
    CurrenciesInPersian = None
    NationalCurrenciesInPersian = None
    GoldsInPersian = None
    MaxExtraServicesFailure = 5

    def __init__(self, token: str, nobitex_tether_service_token: str = None, aban_tether_service_token: str = None) -> None:
        self.tether_service = NobitexService(nobitex_tether_service_token) if nobitex_tether_service_token else AbanTetherService(aban_tether_service_token)
        
        super().__init__(url=f"https://sourcearena.ir/api/?token={token}&currency&v2",
                         source="Navasan.ir", cache_file_name='Navasan.json',
                         tether_service_token=self.tether_service.token, token=token)
        self.get_desired_ones = lambda desired_ones: desired_ones or NavasanService.Defaults
        self.gold_service: GoldService = GoldService(self.token)
        if not NavasanService.NationalCurrenciesInPersian or not NavasanService.GoldsInPersian or not NavasanService.CurrenciesInPersian:
            NavasanService.LoadPersianNames()
        
    @staticmethod
    def LoadPersianNames():
        NavasanService.NationalCurrenciesInPersian, NavasanService.GoldsInPersian = get_persian_currency_names()
        NavasanService.GoldsInPersian = dict(GoldService.GoldsInPersian, **NavasanService.GoldsInPersian)
        NavasanService.CurrenciesInPersian = dict(NavasanService.NationalCurrenciesInPersian, **NavasanService.GoldsInPersian)

    @staticmethod
    def GetPersianName(symbol: str) -> str:
        if NavasanService.CurrenciesInPersian is None or not NavasanService.CurrenciesInPersian:
            NavasanService.LoadPersianNames()
        if symbol not in NavasanService.CurrenciesInPersian:
            raise InvalidInputException('Currency Symbol/Name!')
        return NavasanService.CurrenciesInPersian[symbol]

    def extract_api_response(self, desired_ones: list = None, short_text: bool = True,
                             optional_api_data: list = None) -> str:
        desired_ones = self.get_desired_ones(desired_ones)
        api_data = optional_api_data or self.latest_data

        res_curr = ''
        res_gold = ''
        
        for slug in desired_ones:
            slug_l = slug.lower()
            row: str
            if slug_l in api_data and 'value' in api_data[slug_l]:
                curr = api_data[slug_l]
                price = float(curr['value']) 
                toman: float = 0.0
                usd: float | None = None
                if 'usd' not in curr or not curr['usd']:
                    toman, _ = self.rounded_prices(price, False)
                else:
                    usd, toman = self.rounded_prices(price)

                toman = persianify(toman)
                if price < 0:
                    toman = f"{toman[1:]}-"
                row = f"{NavasanService.CurrenciesInPersian[slug]}: {toman} تومان" + (f" / {usd}$" if usd else '')
            else:
                row = f'{NavasanService.CurrenciesInPersian[slug]}: ❗️ قیمت دریافت نشد.'
                
            if slug in NavasanService.NationalCurrenciesInPersian:
                res_curr += f'🔸 {row}\n'
            else:
                res_gold += f'🔸 {row}\n'
                
        if res_curr:
            res_curr = f'📌 #قیمت_لحظه_ای #بازار_ارز \n{res_curr}\n'
        if res_gold:
            res_gold = f'📌 #قیمت_لحظه_ای #بازار_طلا \n{res_gold}\n'

        return res_curr + res_gold

    async def update_services(self):
        try:
            await self.tether_service.get()
        except Exception as ex:
            log('USDT(Tether) Update Failure', ex, 'USD_T')

    # --------- Currency -----------
    async def get_request(self):
        await self.update_services()
        response = await super(NavasanService, self).get_request(no_cache=True)
        return response.data

    async def get(self, desired_ones: list = None, short_text: bool = True) -> str:
        self.latest_data = await self.get_request()  # update latest
        try:
            await self.gold_service.append_gold_prices(self.latest_data)
        except Exception as ex:
            log('Gold Price Update Failure', ex, 'SourceArenaGolds')

        if self.tether_service.recent_value:
            self.set_tether_tomans(self.tether_service.recent_value)

        try:
            self.set_usd_price(self.latest_data['usd']['value'])
        except Exception as ex:
            log('USD(Dollar) Update Failure', ex, 'USD_T')

        self.cache_data(json.dumps(self.latest_data))
        return self.extract_api_response(desired_ones, short_text=short_text)

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(NavasanService, self).load_cache()['data']
        except:
            self.latest_data = []
        return self.latest_data
    
    def irt_to_usd(self, irt_price: float | int) -> float | int:
        return irt_price / self.UsdInTomans
    
    def irt_to_currencies(self, absolute_amount: float | int, source_unit_slug: str, currencies: list = None) -> str:
        currencies = self.get_desired_ones(currencies)
        res_gold, res_curr = '', ''

        for slug in currencies:
            if slug == source_unit_slug:
                continue
            slug_equalized_price = absolute_amount / float(self.latest_data[slug.lower()]['value'])
            slug_equalized_price = mathematix.persianify(mathematix.cut_and_separate(slug_equalized_price))
            if slug in NavasanService.NationalCurrenciesInPersian:
                res_curr += f'🔸 {slug_equalized_price} {NavasanService.CurrenciesInPersian[slug]}\n'
            else:
                res_gold += f'🔸 {slug_equalized_price} {NavasanService.CurrenciesInPersian[slug]}\n'

        return f'''📌#بازار_ارز
{res_curr}
📌#بازار_طلا
{res_gold}'''

    def equalize(self, source_unit_symbol: str, amount: float | int, target_currencies: list = None) -> Union[str, float | int, float | int]:
        """This function gets an amount param, alongside with a source_unit_symbol [and abviously with the users desired coins]
            and it returns a text string, that in each row of that, shows that amount equivalent in another currency unit."""
        # First check the required data is prepared
        if not self.latest_data:
            raise NoLatestDataException('use for equalizing!')
        if source_unit_symbol not in NavasanService.CurrenciesInPersian:
            raise InvalidInputException('Currency/Gold symbol!')

        # text header
        header: str = ("✅ %s %s" % (mathematix.persianify(amount),
                               NavasanService.CurrenciesInPersian[source_unit_symbol])) + ' معادل است با::\n\n'

        # first row is the equivalent price in USD(the price unit selected by the bot configs.)
        absolute_amount: float = amount * float(
            self.latest_data[source_unit_symbol.lower()]['value'])


        return  header, self.irt_to_currencies(absolute_amount, source_unit_symbol, target_currencies), self.irt_to_usd(absolute_amount), absolute_amount