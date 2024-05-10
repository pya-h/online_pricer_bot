from api.base import *
import json
from tools.exceptions import InvalidInputException
from api.tether_service import AbanTetherService
from tools.manuwriter import log
from tools.mathematix import persianify


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

    @staticmethod
    def LoadPersianNames():
        NavasanService.NationalCurrenciesInPersian, NavasanService.GoldsInPersian = get_persian_currency_names()
        NavasanService.GoldsInPersian = dict(NavasanService.GoldsInPersian, **GoldService.GoldsInPersian)
        NavasanService.CurrenciesInPersian = dict(NavasanService.NationalCurrenciesInPersian, **NavasanService.GoldsInPersian)

    @staticmethod
    def GetPersianName(symbol: str) -> str:
        if NavasanService.CurrenciesInPersian is None or not NavasanService.CurrenciesInPersian:
            NavasanService.LoadPersianNames()
        if symbol not in NavasanService.CurrenciesInPersian:
            raise InvalidInputException('Currency Symbol/Name!')
        return NavasanService.CurrenciesInPersian[symbol]

    def __init__(self, token: str, aban_tether_token: str) -> None:
        super().__init__(url=f"https://sourcearena.ir/api/?token={token}&currency&v2",
                         source="Navasan.ir", cache_file_name='Navasan.json',
                         tether_service_token=aban_tether_token, token=token)
        self.tether_service = AbanTetherService(aban_tether_token)
        self.get_desired_ones = lambda desired_ones: desired_ones or NavasanService.Defaults
        self.gold_service: GoldService = GoldService(self.token)
        if not NavasanService.NationalCurrenciesInPersian or not NavasanService.GoldsInPersian or not NavasanService.CurrenciesInPersian:
            NavasanService.LoadPersianNames()

    def extract_api_response(self, desired_ones: list = None, short_text: bool = True,
                             optional_api_data: list = None) -> str:
        desired_ones = self.get_desired_ones(desired_ones)
        api_data = optional_api_data or self.latest_data
        rows = {}

        res_curr = ''
        res_gold = ''
        
        for slug in desired_ones:
            slug_l = slug.lower()
            curr = api_data[slug_l]
            price = float(curr['value'])
            toman: float = 0.0
            usd: float | None = None
            
            if 'usd' not in curr or not curr['usd']:
                toman, _ = self.rounded_prices(price, False)
            else:
                usd, toman = self.rounded_prices(price)

            toman = persianify(toman)
            row = f"{NavasanService.CurrenciesInPersian[slug]}: {toman} تومان" + (f" / {usd}$" if usd else '')

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
        except:
            pass

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
            log('Cant get source arena gold prices', ex, 'SourceArenaGolds')
        if self.tether_service.recent_response:
            self.set_tether_tomans(self.tether_service.recent_response)
        elif not self.TetherInTomans or self.tether_service.no_response_counts > NavasanService.MaxExtraServicesFailure:
            try:
                '''second tether service'''
            except:
                if not NavasanService.TetherInTomans:
                    NavasanService.TetherInTomans = NavasanService.DefaultTetherInTomans

        try:
            self.set_usd_price(self.latest_data['usd']['value'])
        except:
            if not NavasanService.UsdInTomans:
                NavasanService.UsdInTomans = NavasanService.DefaultUsbInTomans

        self.cache_data(json.dumps(self.latest_data))
        self.tether_service.cache_data(self.tether_service.summary(),
                                       custom_file_name='tether')
        return self.extract_api_response(desired_ones, short_text=short_text)

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(NavasanService, self).load_cache()['data']
        except:
            self.latest_data = []
        return self.latest_data

    # def equalizer_row(self, unit_symbol: str, value: float|int):
    #     '''returns the row shape/format of the equalizing coin.'''
    #     value_cut = cut_and_separate(value)
    #     value = persianify(value_cut)
    #     return f'🔸 {value} {CryptoCurrency.CoinsInPersian[unit_symbol]}\n'

    # def tomans_to_currencies(self, absolute_amount: float|int, source_unit_symbol: str, currencies: list = None) -> str:
    #     currencies = self.get_desired_ones(currencies)

    #     for curr in self.latest_data:
    #         slug = curr['slug'].upper()
    #         price = float(curr['price']) / 10 if slug not in Navasan.EntitiesInDollars else float(curr['price'])

    #         if slug in currencies:
    #             # repetitive code OR using multiple conditions (?)
    #             if slug not in Navasan.EntitiesInDollars:
    #                 toman, _ = self.rounded_prices(price, False)
    #                 toman = persianify(toman)
    #                 rows[slug] = f"{Navasan.CurrenciesInPersian[slug]}: {toman} تومان"
    #             else:
    #                 usd, toman = self.rounded_prices(price)
    #                 toman = persianify(toman)
    #                 rows[slug] = f"{Navasan.CurrenciesInPersian[slug]}: {toman} تومان / {usd}$"

    #     for item in currencies:
    #         curr =
    #         if item == source_unit_symbol:
    #             continue
    #         amount_in_this_item_unit = absolute_amount  / float(self.latest_data[item][0]['quote'][self.price_unit]['price'])
    #         res += self.equalizer_row(item, amount_in_this_item_unit)

    #     return res

    # def equalize(self, source_unit_symbol: str, amount: float|int, desired_currencies: list = None) -> str:

    #     # text header
    #     res: str = f'💱☯ معادل سازی ♻️💱\nبا توجه به آخرین قیمت های بازار ارز  ' + \
    #         ("%s %s" % (persianify(amount), Navasan.CurrenciesInPersian[source_unit_symbol])) + ' معادل است با:\n\n'

    #     # first row is the equivalent price in USD(the price unit selected by the bot configs.)
    #     source = list(filter(lambda curr: curr['slug'].upper() == source_unit_symbol, self.latest_data))
    #     if not source:
    #         raise InvalidInputException('currency sumbol')

    #     absolute_amount: float = amount * float(self.latest_data[source_unit_symbol][0]['quote'][self.price_unit]['price'])

    #     abs_usd, abs_toman = self.rounded_prices(absolute_amount, tether_as_unit_price=True)
    #     res += f'🔸 {persianify(abs_usd)} {Navasan.GetPersianName(BaseAPIService.DOLLAR_SYMBOL)}\n'

    #     res += f'🔸 {persianify(abs_toman)} تومان\n'

    #     res += self.usd_to_cryptos(absolute_amount, source_unit_symbol, desired_currencies)

    #     return res
