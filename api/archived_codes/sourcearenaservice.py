from api.currency_service import CurrencyService, get_persian_currency_names
from tools.exceptions import InvalidInputException
from tools.mathematix import persianify
from typing import Dict
from api.tether_service import AbanTetherService


class SourceArenaService(CurrencyService):
    Defaults = ("USD", "EUR", "AED", "GBP", "TRY", 'ONS', 'TALA_18', 'TALA_MESGHAL', 'SEKE_EMAMI', 'SEKE_GERAMI',)
    EntitiesInDollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
    CurrenciesInPersian = None
    NationalCurrenciesInPersian = None
    GoldsInPersian = None
    MaxExtraServicesFailure = 5

    @staticmethod
    def LoadPersianNames():
        SourceArenaService.NationalCurrenciesInPersian, SourceArenaService.GoldsInPersian = get_persian_currency_names()
        SourceArenaService.CurrenciesInPersian = dict(SourceArenaService.NationalCurrenciesInPersian, **SourceArenaService.GoldsInPersian)

    @staticmethod
    def GetPersianName(symbol: str) -> str:
        if SourceArenaService.CurrenciesInPersian is None or not SourceArenaService.CurrenciesInPersian:
            SourceArenaService.LoadPersianNames()
        if symbol not in SourceArenaService.CurrenciesInPersian:
            raise InvalidInputException('Currency Symbol/Name!')
        return SourceArenaService.CurrenciesInPersian[symbol]

    def __init__(self, token: str, aban_tether_token: str) -> None:
        super().__init__(url=f"https://sourcearena.ir/api/?token={token}&currency",
                         source="Sourcearena.ir", cache_file_name='sourcearena.json',
                         tether_service_token=aban_tether_token, token=token)
        if not SourceArenaService.NationalCurrenciesInPersian or not SourceArenaService.GoldsInPersian or not SourceArenaService.CurrenciesInPersian:
            SourceArenaService.LoadPersianNames()

        self.tether_service = AbanTetherService(aban_tether_token)
        self.get_desired_ones = lambda desired_ones: desired_ones or SourceArenaService.Defaults
        self.direct_prices: Dict[str, float] = {}

    def extract_api_response(self, desired_ones: list = None, short_text: bool = True,
                             optional_api_data: list = None) -> str:
        desired_ones = self.get_desired_ones(desired_ones)
        api_data = optional_api_data or self.latest_data
        rows = {}

        for curr in api_data:
            slug = curr['slug'].upper()
            price = float(curr['price']) / 10 if slug not in SourceArenaService.EntitiesInDollars else float(curr['price'])
            self.direct_prices[slug] = price
            if slug in desired_ones:
                # repetitive code OR using multiple conditions (?)
                if slug not in SourceArenaService.EntitiesInDollars:
                    toman, _ = self.rounded_prices(price, False)
                    toman = persianify(toman)
                    rows[slug] = f"{SourceArenaService.CurrenciesInPersian[slug]}: {toman} تومان"
                else:
                    usd, toman = self.rounded_prices(price)
                    toman = persianify(toman)
                    rows[slug] = f"{SourceArenaService.CurrenciesInPersian[slug]}: {toman} تومان / {usd}$"

        res_curr = ''
        res_gold = ''
        for slug in desired_ones:

            if slug in SourceArenaService.NationalCurrenciesInPersian:
                res_curr += f'🔸 {rows[slug]}\n' if slug in rows else f'❗️ {SourceArenaService.CurrenciesInPersian[slug]}: قیمت دریافت نشد.\n'
            else:
                res_gold += f'🔸 {rows[slug]}\n' if slug in rows else f'❗️ {SourceArenaService.CurrenciesInPersian[slug]}: قیمت دریافت نشد.\n'
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
        response = await super(SourceArenaService, self).get_request(no_cache=True)
        return response.data["data"] if 'data' in response.data else [], response.text

    async def get(self, desired_ones: list = None, short_text: bool = True) -> str:
        self.latest_data, response_text = await self.get_request()  # update latest

        usd_t = {curr['slug']: curr for curr in \
                 list(filter(lambda d: d['slug'].upper() == 'TETHER' or d['slug'].upper() == 'USD', self.latest_data))}

        if self.tether_service.recent_value:
            self.set_tether_tomans(self.tether_service.recent_value)
            usd_t['TETHER']['price'] = self.tether_service.recent_value
        elif not self.TetherInTomans or self.tether_service.no_response_counts > SourceArenaService.MaxExtraServicesFailure:
            try:
                self.set_tether_tomans((float(usd_t['TETHER']['price']) / 10.0) or SourceArenaService.DefaultTetherInTomans)
            except:
                if not SourceArenaService.TetherInTomans:
                    SourceArenaService.TetherInTomans = SourceArenaService.DefaultTetherInTomans

        try:
            self.set_usd_price(self.tether_service.guess_dollar_price() or (
                        float(usd_t['USD']['price']) / 10.0) or SourceArenaService.DefaultUsbInTomans)
            usd_t['USD'][
                'price'] = self.UsdInTomans * 10.0  # in dict must be in fuckin rials; this fuckin country with its fuckin worthless currency
        except:
            if not SourceArenaService.UsdInTomans:
                SourceArenaService.UsdInTomans = SourceArenaService.DefaultUsbInTomans

        self.cache_data(response_text)
        self.tether_service.cache_data(self.tether_service.summary(),
                                       custom_file_name='usd_t')
        return self.extract_api_response(desired_ones, short_text=short_text)

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(SourceArenaService, self).load_cache()['data']
        except:
            self.latest_data = []
        return self.latest_data
