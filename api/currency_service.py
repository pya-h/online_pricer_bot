from api.base import *
from tools.exceptions import InvalidInputException
import json
from api.price_seek import PriceSeek
from datetime import datetime
from random import randint


def get_persian_currency_names() -> tuple:
    currency_names_fa = "{}"
    gold_names_fa = "{}"
    try:
        json_file = open("./api/national-currencies.fa.json", "r")
        currency_names_fa = json_file.read()
        json_file.close()
        json_file = open("./api/golds.fa.json", "r")
        gold_names_fa = json_file.read()
        json_file.close()
    except Exception as e:
        print(e)
        pass

    return json.loads(currency_names_fa), json.loads(gold_names_fa)


class AbanTether(BaseAPIService):
    TetherSymbol = 'USDT'
    def __init__(self, token: str) -> None:
        self.token = token
        super(AbanTether, self).__init__(url=f'https://abantether.com/api/v1/otc/coin-price?coin={AbanTether.TetherSymbol}',
                                            source="Abantether.com")
        self.headers = {'Authorization': f'Token {self.token}'}
        self.recent_response: float|None = None
        self.recent_total_response: dict = {}
        self.no_response_counts: int = 0
        self.last_guess_date: datetime = mathematix.tz_today()
        self.usd_recent_guess: int = 0
        
    async def get(self):
        self.recent_total_response = await self.get_request(headers=self.headers)
        self.no_response_counts += 1
        self.recent_response = None
        if self.recent_total_response and AbanTether.TetherSymbol in self.recent_total_response:
            value = self.recent_total_response[AbanTether.TetherSymbol]
            mid = (float(value['irtPriceBuy']) + float(value['irtPriceSell'])) / 2.0
            self.recent_response = mid
            self.no_response_counts = 0
            return mid

        return None

    def summary(self, dollor_price: float) -> str:
        tether = self.recent_total_response[AbanTether.TetherSymbol]
        tether['irtMidPoint'] = self.recent_response
        tether['USD'] = dollor_price
        return json.dumps(tether)

    def time_for_next_guess(self) -> int:
        if not self.recent_response:
            return False
        if not self.usd_recent_guess:
            return True
        diff, self.last_guess_date = mathematix.from_now_time_diff(self.last_guess_date)
        if diff < 60:
            return False
        return self.last_guess_date.hour >= 10 and self.last_guess_date.hour < 22
    
    def guess_dollar_price(self, guess_range: int = 100) -> int:
        if not self.time_for_next_guess():
            return self.usd_recent_guess
        diff = randint(1, guess_range)
        self.usd_recent_guess = self.recent_response - diff
        return self.usd_recent_guess

class SourceArena(APIService):
    Defaults = ("USD", "EUR", "AED", "GBP", "TRY", 'ONS', 'TALA_18', 'TALA_MESGHAL', 'SEKE_EMAMI', 'SEKE_GERAMI',)
    EntitiesInDollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
    CurrenciesInPersian = None
    NationalCurrenciesInPersian = None
    GoldsInPersian = None

    MaxExtraServicesFailure = 5

    DefaultTetherInTomans = 61300
    DefaultUsbInTomans = 61000

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
        self.token = token

        if not SourceArena.NationalCurrenciesInPersian or not SourceArena.GoldsInPersian or not SourceArena.CurrenciesInPersian:
            SourceArena.LoadPersianNames()

        super(SourceArena, self).__init__(url=f"https://sourcearena.ir/api/?token={self.token}&currency",
                                          source="Sourcearena.ir", cache_file_name='sourcearena.json')
        self.aban_tether_token = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Nzg2NzUiLCJpYXQiOjE2OTc2NDcyNTAsImV4cCI6MTcyOTE4MzI1MH0.QfVVufZo8VEtrkbRGoakINgWfyHLPVEcWWnx26nSZ6M'
        self.tether_service = AbanTether(aban_tether_token)
        self.usd_service = PriceSeek()
        self.get_desired_ones = lambda desired_ones: desired_ones or SourceArena.Defaults

    def extract_api_response(self, desired_ones: list=None, short_text: bool=True, optional_api_data:list = None) -> str:
        desired_ones = self.get_desired_ones(desired_ones)
        api_data = optional_api_data or self.latest_data
        rows = {}

        for curr in api_data:
            slug = curr['slug'].upper()
            price = float(curr['price']) / 10 if slug not in SourceArena.EntitiesInDollars else float(curr['price'])

            if slug in desired_ones:
                # repetitive code OR using multiple conditions (?)
                if slug not in SourceArena.EntitiesInDollars:
                    toman, _ = self.rounded_prices(price, False)
                    toman = mathematix.persianify(toman)
                    rows[slug] = f"{SourceArena.CurrenciesInPersian[slug]}: {toman} تومان"
                else:
                    usd, toman = self.rounded_prices(price)
                    toman = mathematix.persianify(toman)
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
            await self.usd_service.get_value()
        except:
            pass
        try:
            await self.tether_service.get()
        except:
            pass

    # --------- Currency -----------
    async def get_request(self):
        await self.update_services()

        response = await super(SourceArena, self).get_request(no_cache=True)

        return response.data["data"] if 'data' in response.data else [], response.text

    async def get(self, desired_ones: list=None, short_text: bool=True) -> str:
        self.latest_data, response_text = await self.get_request()  # update latest

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
                    
        if self.usd_service.recent_response:
            self.set_usd_price(self.usd_service.recent_response)
            usd_t['USD']['price'] = self.usd_service.recent_response
        elif not self.UsdInTomans or self.usd_service.no_response_counts > SourceArena.MaxExtraServicesFailure:
            # TODO: INFORM THIS TO SUNSCRIBER ADMINS
            try:
                self.set_usd_price(self.tether_service.guess_dollar_price() or (float(usd_t['USD']['price']) / 10.0) or SourceArena.DefaultUsbInTomans)
            except:
                if not SourceArena.UsdInTomans:
                    SourceArena.UsdInTomans = SourceArena.DefaultUsdInTomans
                    
        self.cache_data(response_text)
        self.tether_service.cache_data(self.tether_service.summary(self.usd_service.recent_response), custom_file_name='usd_t')
        return self.extract_api_response(desired_ones, short_text=short_text)

    def load_cache(self) -> list|dict:
        try:
            self.latest_data = super(SourceArena, self).load_cache()['data']
        except:
            self.latest_data = []
        return self.latest_data
