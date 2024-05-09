from api.currency_service import CurrencyService, get_persian_currency_names
from tools.exceptions import InvalidInputException
from tools.mathematix import persianify
from typing import Dict
from tether_service import AbanTether


class SourceArena(CurrencyService):
    Defaults = ("USD", "EUR", "AED", "GBP", "TRY", 'ONS', 'TALA_18', 'TALA_MESGHAL', 'SEKE_EMAMI', 'SEKE_GERAMI',)
    EntitiesInDollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
    CurrenciesInPersian = None
    NationalCurrenciesInPersian = None
    GoldsInPersian = None
    MaxExtraServicesFailure = 5

    @staticmethod
    def LoadPersianNames():
        SourceArena.NationalCurrenciesInPersian, SourceArena.GoldsInPersian = get_persian_currency_names()
        SourceArena.CurrenciesInPersian = dict(SourceArena.NationalCurrenciesInPersian, **SourceArena.GoldsInPersian)

    @staticmethod
    def GetPersianName(symbol: str) -> str:
        if SourceArena.CurrenciesInPersian is None or not SourceArena.CurrenciesInPersian:
            SourceArena.LoadPersianNames()
        if symbol not in SourceArena.CurrenciesInPersian:
            raise InvalidInputException('Currency Symbol/Name!')
        return SourceArena.CurrenciesInPersian[symbol]

    def __init__(self, token: str, aban_tether_token: str) -> None:
        super().__init__(url=f"https://sourcearena.ir/api/?token={token}&currency",
                         source="Sourcearena.ir", cache_file_name='sourcearena.json',
                         tether_service_token=aban_tether_token, token=token)
        if not SourceArena.NationalCurrenciesInPersian or not SourceArena.GoldsInPersian or not SourceArena.CurrenciesInPersian:
            SourceArena.LoadPersianNames()

        self.tether_service = AbanTether(aban_tether_token)
        self.get_desired_ones = lambda desired_ones: desired_ones or SourceArena.Defaults
        self.direct_prices: Dict[str, float] = {}

    def extract_api_response(self, desired_ones: list = None, short_text: bool = True,
                             optional_api_data: list = None) -> str:
        desired_ones = self.get_desired_ones(desired_ones)
        api_data = optional_api_data or self.latest_data
        rows = {}

        for curr in api_data:
            slug = curr['slug'].upper()
            price = float(curr['price']) / 10 if slug not in SourceArena.EntitiesInDollars else float(curr['price'])
            self.direct_prices[slug] = price
            if slug in desired_ones:
                # repetitive code OR using multiple conditions (?)
                if slug not in SourceArena.EntitiesInDollars:
                    toman, _ = self.rounded_prices(price, False)
                    toman = persianify(toman)
                    rows[slug] = f"{SourceArena.CurrenciesInPersian[slug]}: {toman} تومان"
                else:
                    usd, toman = self.rounded_prices(price)
                    toman = persianify(toman)
                    rows[slug] = f"{SourceArena.CurrenciesInPersian[slug]}: {toman} تومان / {usd}$"

        res_curr = ''
        res_gold = ''
        for slug in desired_ones:

            if slug in SourceArena.NationalCurrenciesInPersian:
                res_curr += f'🔸 {rows[slug]}\n' if slug in rows else f'❗️ {SourceArena.CurrenciesInPersian[slug]}: قیمت دریافت نشد.\n'
            else:
                res_gold += f'🔸 {rows[slug]}\n' if slug in rows else f'❗️ {SourceArena.CurrenciesInPersian[slug]}: قیمت دریافت نشد.\n'
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
        response = await super(SourceArena, self).get_request(no_cache=True)
        return response.data["data"] if 'data' in response.data else [], response.text

    async def get(self, desired_ones: list = None, short_text: bool = True) -> str:
        self.latest_data, response_text = await self.get_request()  # update latest

        # FIXME: AFTER IMPLEMENTING NAVASAN API, THERE IS NO NEED TO SEARCH LIKE THIS, RESULT IS DICT
        # FIXME: CHECK

        usd_t = {curr['slug']: curr for curr in \
                 list(filter(lambda d: d['slug'].upper() == 'TETHER' or d['slug'].upper() == 'USD', self.latest_data))}

        if self.tether_service.recent_response:
            self.set_tether_tomans(self.tether_service.recent_response)
            usd_t['TETHER']['price'] = self.tether_service.recent_response
        elif not self.TetherInTomans or self.tether_service.no_response_counts > SourceArena.MaxExtraServicesFailure:
            try:
                self.set_tether_tomans((float(usd_t['TETHER']['price']) / 10.0) or SourceArena.DefaultTetherInTomans)
            except:
                if not SourceArena.TetherInTomans:
                    SourceArena.TetherInTomans = SourceArena.DefaultTetherInTomans

        try:
            self.set_usd_price(self.tether_service.guess_dollar_price() or (
                        float(usd_t['USD']['price']) / 10.0) or SourceArena.DefaultUsbInTomans)
            usd_t['USD'][
                'price'] = self.UsdInTomans * 10.0  # in dict must be in fuckin rials; this fuckin country with its fuckin worthless currency
        except:
            if not SourceArena.UsdInTomans:
                SourceArena.UsdInTomans = SourceArena.DefaultUsbInTomans

        self.cache_data(response_text)
        self.tether_service.cache_data(self.tether_service.summary(),
                                       custom_file_name='usd_t')
        return self.extract_api_response(desired_ones, short_text=short_text)

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(SourceArena, self).load_cache()['data']
        except:
            self.latest_data = []
        return self.latest_data

    # def equalizer_row(self, unit_symbol: str, value: float|int):
    #     '''returns the row shape/format of the equalizing coin.'''
    #     value_cut = mathematix.cut_and_separate(value)
    #     value = mathematix.persianify(value_cut)
    #     return f'🔸 {value} {CryptoCurrency.CoinsInPersian[unit_symbol]}\n'

    # def tomans_to_currencies(self, absolute_amount: float|int, source_unit_symbol: str, currencies: list = None) -> str:
    #     currencies = self.get_desired_ones(currencies)

    #     for curr in self.latest_data:
    #         slug = curr['slug'].upper()
    #         price = float(curr['price']) / 10 if slug not in SourceArena.EntitiesInDollars else float(curr['price'])

    #         if slug in currencies:
    #             # repetitive code OR using multiple conditions (?)
    #             if slug not in SourceArena.EntitiesInDollars:
    #                 toman, _ = self.rounded_prices(price, False)
    #                 toman = mathematix.persianify(toman)
    #                 rows[slug] = f"{SourceArena.CurrenciesInPersian[slug]}: {toman} تومان"
    #             else:
    #                 usd, toman = self.rounded_prices(price)
    #                 toman = mathematix.persianify(toman)
    #                 rows[slug] = f"{SourceArena.CurrenciesInPersian[slug]}: {toman} تومان / {usd}$"

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
    #         ("%s %s" % (mathematix.persianify(amount), SourceArena.CurrenciesInPersian[source_unit_symbol])) + ' معادل است با:\n\n'

    #     # first row is the equivalent price in USD(the price unit selected by the bot configs.)
    #     source = list(filter(lambda curr: curr['slug'].upper() == source_unit_symbol, self.latest_data))
    #     if not source:
    #         raise InvalidInputException('currency sumbol')

    #     absolute_amount: float = amount * float(self.latest_data[source_unit_symbol][0]['quote'][self.price_unit]['price'])

    #     abs_usd, abs_toman = self.rounded_prices(absolute_amount, tether_as_unit_price=True)
    #     res += f'🔸 {mathematix.persianify(abs_usd)} {SourceArena.GetPersianName(BaseAPIService.DOLLAR_SYMBOL)}\n'

    #     res += f'🔸 {mathematix.persianify(abs_toman)} تومان\n'

    #     res += self.usd_to_cryptos(absolute_amount, source_unit_symbol, desired_currencies)

    #     return res

