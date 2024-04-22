from api.base import *
from tools.exceptions import InvalidInputException

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

    def get(self):
        response = self.send_request(headers=self.headers)
        self.recent_response = None
        if response and AbanTether.TetherSymbol in response:
            value = response[AbanTether.TetherSymbol]
            mid = (float(value['irtPriceBuy']) + float(value['irtPriceSell'])) / 2.0
            self.recent_response = mid
            return mid
        
        return None


class SourceArena(APIService):
    Defaults = ("USD", "EUR", "AED", "GBP", "TRY", 'ONS', 'TALA_18', 'TALA_MESGHAL', 'SEKE_EMAMI', 'SEKE_GERAMI',)
    EntitiesInDollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
    CurrenciesInPersian = None
    NationalCurrenciesInPersian = None
    GoldsInPersian = None

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

    def get_desired_ones(self, desired_ones: list) -> list:
        if not desired_ones:
            desired_ones = SourceArena.Defaults
        return desired_ones

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
                res_curr += f'🔸 {rows[slug]}\n' if slug in rows else f'❗️ {SourceArena.CurrenciesInPersian[slug]: قیمت دریافت نشد.}'
            else:
                res_gold += f'🔸 {rows[slug]}\n' if slug in rows else f'❗️ {SourceArena.CurrenciesInPersian[slug]: قیمت دریافت نشد.}'
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
            self.tether_service.get()
        except:
            pass
        
    # --------- Currency -----------
    async def send_request(self):
        await self.update_services()

        response = super(SourceArena, self).send_request(no_cache=True)
        return response["data"] if 'data' in response else []


    async def get(self, desired_ones: list=None, short_text: bool=True) -> str:
        self.latest_data = await self.send_request()  # update latest
        usd_t = {curr['slug']: curr for curr in \
            list(filter(lambda d: d['slug'].upper() == 'TETHER' or d['slug'].upper() == 'USD', self.latest_data))}
        print(usd_t)
        if self.usd_service.recent_response:
            self.set_usd_price(self.usd_service.recent_response)
            usd_t['USD']['price'] = self.usd_service.recent_response
        if self.tether_service.recent_response:
            self.set_tether_tomans(self.tether_service.recent_response)
            usd_t['TETHER']['price'] = self.tether_service.recent_response
        self.cache_data(self.dumps(self.latest_data))
        return self.extract_api_response(desired_ones, short_text=short_text)

    def load_cache(self) -> list|dict:
        try:
            self.latest_data = super(SourceArena, self).load_cache()['data']
        except:
            self.latest_data = []
        return self.latest_data
