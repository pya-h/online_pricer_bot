from api.manager import *
from flag import flag

CURRENCIES_PERSIAN_NAMES = {
    "USD": "دلار (آمریکا)",
    "EUR": "یورو (اروپا)",
    "AED": "درهم (امارات)",
    "GBP": "پوند (انگلیس)",
    "TRY": "لیر (ترکیه)",
    "CHF": "فرانک (سوئیس)",
    "CNY": "یوان (چین)",
    "JPY": "ین (ژاپن)",
    "KRW": "وون (کره جنوبی)",
    "CAD": "دلار (کانادا)",
    "AUD": "دلار (استرالیا)",
    "NZD": "دلار (نیوزیلند)",
    "SGD": "دلار (سنگاپور)",
    "HKD": "دلار (هنگ کنگ)",
    "INR": "روپیه (هند)",
    "PKR": "روپیه (پاکستان)",
    "AFN": "افغانی (افغانستان)",
    "DKK": "کرون (دانمارک)",
    "SEK": "کرون (سوئد)",
    "NOK": "کرون (نروژ)",
    "SAR": "ریال (عربستان)",
    "QAR": "ریال (قطر)",
    "OMR": "ریال (عمان)",
    "KWD": "دینار (کویت)",
    "BHD": "دینار (بحرین)",
    "IQD": "دینار (عراق)",
    "MYR": "رینگیت (مالزی)",
    "THB": "بات (تایلند)",
    "RUB": "روبل (روسیه)",
    "AZN": "منات (آذربایجان)",
    "TMM": "منات (ترکمنستان)",
    "AMD": "درام (ارمنستان)",
    "GEL": "لاری (گرجستان)",
    "KGS": "سوم (قرقیزستان)",
    "TJS": "سامانی (تاجیکستان)",
    "SYP": "لیر (سوریه)",
}

GOLDS_PERSIAN_NAMES = {
    "ONS": "انس طلا",
    "ONSNOGHRE": "انس نقره",
    "PALA": "انس پلاتین",
    "ONSPALA": "انس پالادیوم",
    "OIL": "نفت سبک",
    "TALA_18": "طلا 18 عیار",
    "TALA_24": "طلا 24 عیار",
    "TALA_MESGHAL": "مثقال طلا",
    "SEKE_EMAMI": "سکه امامی",
    "SEKE_BAHAR": "سکه بهار آزادی",
    "SEKE_NIM": "نیم سکه",
    "SEKE_ROB": "ربع سکه",
    "SEKE_GERAMI": "سکه گرمی",
}

# CURRENCY_FLAG_ICONS = {
#     "USD": ":us:",
#     "EUR": ":eu:",
#     "AED": ":aE:",
#     "GBP": ":gb:",
#     "TRY": ':tr:',
#     "CHF": ':ch:',
#     "CNY": ":cn:",
#     "JPY": ":jp:",
#     "KRW": ":kr:",
#     "CAD": ":ca:",
#     "AUD": ":au:",
#     "NZD": ":nz:",
#     "SGD": ":sg:",
#     "HKD": ":hk:",
#     "INR": ":in:",
#     "PKR": ":pk:",
#     "AFN": ":af:",
#     "DKK": ":dk:",
#     "SEK": ":se:",
#     "NOK": ":no:",
#     "SAR": ":SA:",
#     "QAR": ":qa:",
#     "OMR": ":om:",
#     "KWD": ":kw:",
#     "BHD": ":bh:",
#     "IQD": ":iq:",
#     "MYR": ":my:",
#     "THB": ":th:",
#     "RUB": ":ru:",
#     "AZN": ":az:",
#     "TMM": ":tm:",
#     "AMD": ":am:",
#     "GEL": ":ge:",
#     "KGS": ":kg:",
#     "TJS": ":tj:",
#     "SYP": ":sy:",
# }

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

    def __init__(self, token: str, aban_tether_token: str) -> None:
        self.token = token
        super(SourceArena, self).__init__(url=f"https://sourcearena.ir/api/?token={self.token}&currency",
                                          source="Sourcearena.ir", cache_file_name='sourcearena.json',
                                          dict_persian_names=dict(CURRENCIES_PERSIAN_NAMES, **GOLDS_PERSIAN_NAMES))
        self.just_gold_names, self.just_currency_names = GOLDS_PERSIAN_NAMES, CURRENCIES_PERSIAN_NAMES
        self.aban_tether_token = 'Token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4Nzg2NzUiLCJpYXQiOjE2OTc2NDcyNTAsImV4cCI6MTcyOTE4MzI1MH0.QfVVufZo8VEtrkbRGoakINgWfyHLPVEcWWnx26nSZ6M'
        self.tetherManager = AbanTether(aban_tether_token)
        self.tether_manager_respond = False


    def get_desired_ones(self, desired_ones: list) -> list:
        if not desired_ones:
            desired_ones = SourceArena.Defaults
        return desired_ones

    def extract_api_response(self, desired_ones: list=None, short_text: bool=True) -> str:
        desired_ones = self.get_desired_ones(desired_ones)

        rows = {}
        for curr in self.latest_data:
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
                    rows[slug] = f"{self.dict_persian_names[slug]}: {toman} تومان"
                else:
                    usd, toman = self.rounded_prices(price)
                    toman = mathematix.persianify(toman)
                    rows[slug] = f"{self.dict_persian_names[slug]}: {toman} تومان / {usd}$"

        res_curr = ''
        res_gold = ''
        for slug in desired_ones:
            if slug in self.just_currency_names:  # just currencies have flag
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
