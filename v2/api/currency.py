from api.manager import *
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


class AbanTether(BaseAPIManager):
    TetherSymbol = 'USDT'
    def __init__(self, token: str) -> None:
        self.token = token
        super(AbanTether, self).__init__(url=f'https://abantether.com/api/v1/otc/coin-price?coin={AbanTether.TetherSymbol}',
                                            source="Abantether.com")
        self.headers = {'Authorization': f'Token {self.token}'}

    def get(self):
        response = self.send_request(headers=self.headers)
        if response and AbanTether.TetherSymbol in response:
            value = response[AbanTether.TetherSymbol]
            return (float(value['irtPriceBuy']) + float(value['irtPriceSell'])) / 2.0
        return None


class SourceArena(APIManager):
    Defaults = ("USD", "EUR", "AED", "GBP", "TRY", 'ONS', 'TALA_18', 'TALA_MESGHAL', 'SEKE_EMAMI', 'SEKE_GERAMI',)
    EntitiesIndollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
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
        self.tetherManager = AbanTether(aban_tether_token)
        self.tether_manager_respond = False

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
            price = float(curr['price']) / 10 if slug not in SourceArena.EntitiesIndollars else float(curr['price'])
            if slug == 'USD':
                self.set_usd_price(price)
            elif not self.tether_manager_respond and slug == 'TETHER':
                # if aban tether not responded successful, set the tether price from source arena
                self.set_tether_tomans(price)

            if slug in desired_ones:
                # repetitive code OR using multiple conditions (?)
                if slug not in SourceArena.EntitiesIndollars:
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
                res_curr += f'🔸 {rows[slug]}\n'
            else:
                res_gold += f'🔸 {rows[slug]}\n'
        if res_curr:
            res_curr = f'📌 #قیمت_لحظه_ای #بازار_ارز 👇\n{res_curr}\n'
        if res_gold:
            res_gold = f'📌 #قیمت_لحظه_ای #بازار_طلا 👇\n{res_gold}\n'
        return res_curr + res_gold

    # --------- Currency -----------
    def send_request(self):
        # first try to set tether irr price from AbanTether
        self.tether_manager_respond = False
        try:
            result = self.tetherManager.get()
            if result:
                self.set_tether_tomans(result)
                self.tether_manager_respond = True
        except:
            pass

        response = super(SourceArena, self).send_request()
        return response["data"] if 'data' in response else []
