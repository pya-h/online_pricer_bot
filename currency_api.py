from api_manager import *
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

    "ONS": "انس طلا",
    "TALA_MESGHAL": "مثقال طلا",
    "TALA_18": "طلا 18 عیار",
    "TALA_24": "طلا 24 عیار",
    "SEKE_EMAMI": "سکه امامی",
    "SEKE_BAHAR": "سکه بهار آزادی",
    "SEKE_NIM": "نیم سکه",
    "SEKE_ROB": "ربع سکه",
    "SEKE_GERAMI": "سکه گرمی",
    "ONSNOGHRE": "انس نقره",
    "PALA": "انس پلاتین",
    "ONSPALA": "انس پلادیوم",
    "OIL": "نفت سبک",

}


FLAG_ICONS = {
    "USD": ":us:",
    "EUR": ":eu:",
    "AED": ":aE:",
    "GBP": ":gb:",
    "TRY": ':tr:',
    "CHF": ':ch:',
    "CNY": ":cn:",
    "JPY": ":jp:",
    "KRW": ":kr:",
    "CAD": ":ca:",
    "AUD": ":au:",
    "NZD": ":nz:",
    "SGD": ":sg:",
    "HKD": ":hk:",
    "INR": ":in:",
    "PKR": ":pk:",
    "AFN": ":af:",
    "DKK": ":dk:",
    "SEK": ":se:",
    "NOK": ":no:",
    "SAR": ":SA:",
    "QAR": ":qa:",
    "OMR": ":om:",
    "KWD": ":kw:",
    "BHD": ":bh:",
    "IQD": ":iq:",
    "MYR": ":my:",
    "THB": ":th:",
    "RUB": ":ru:",
    "AZN": ":az:",
    "TMM": ":tm:",
    "AMD": ":am:",
    "GEL": ":ge:",
    "KGS": ":kg:",
    "TJS": ":tj:",
    "SYP": ":sy:",
}
class SourceArena(APIManager):
    Defaults = ["USD", "EUR", "AED", "GBP", "TRY", 'ONS', 'TALA_18', 'SEKE_EMAMI', 'SEKE_BAHAR', 'SEKE_GERAMI', ]

    def __init__(self, token, params=None) -> None:
        self.token = token
        super(SourceArena, self).__init__(url=f"https://sourcearena.ir/api/?token={self.token}&currency", source="Sourcearena.ir", dict_persian_names=CURRENCIES_PERSIAN_NAMES
            , icons=FLAG_ICONS)


    def get_desired_ones(self, desired_ones):
        if not desired_ones:
            desired_ones = SourceArena.Defaults
        return desired_ones


    def extract_api_response(self, desired_ones=None, short_text=True):
        desired_ones = self.get_desired_ones(desired_ones)

        rows = {}
        for curr in self.latest_data:
            slug = curr['slug'].upper()
            price = float(curr['price']) / 10 if slug != 'ONS' else float(curr['price'])
            if slug == 'USD':
                self.set_usd_price(price)
            if slug in desired_ones:
                if slug != 'ONS':
                    toman, _ = self.rounded_prices(price, False)
                    rows[slug] = f"{self.dict_persian_names[slug]}: {toman:,} تومان"
                else:
                    usd, toman = self.rounded_prices(price)
                    rows[slug] = f"{self.dict_persian_names[slug]}: {toman:,} تومان / {usd:,}$"

        res_curr = ''
        res_gold = ''
        for slug in desired_ones:
            if slug in self.icons:  # just currencies have flag
                res_curr += f'{flag(self.icons[slug])} {rows[slug]}\n'
            else:
                res_gold +=  f'🔸 {rows[slug]}\n'
        if res_curr:
            res_curr = f'📌 قیمت لحظه ای بازار ارز:\n{res_curr}\n'
        if res_gold:
            res_gold = f'📌 قیمت لحظه ای بازار طلا:\n{res_gold}\n'
        return res_curr + res_gold

    # --------- Currency -----------
    def send_request(self):
        response = super(SourceArena, self).send_request()
        return response["data"] if 'data' in response else []

