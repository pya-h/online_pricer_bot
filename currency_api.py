from api_manager import *

CURRENCIES = {
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


class SourceArena(APIManager):

    def __init__(self, token, params=None) -> None:
        self.token = token
        super(SourceArena, self).__init__(url=f"https://sourcearena.ir/api/?token={self.token}&currency", source="Sourcearena.ir", dict_persian_names=CURRENCIES)

    def extract_api_response(self, desired_ones=None):
        desired_ones = self.get_desired_ones(desired_ones)

        res = ''
        for curr in self.latest_data:
            slug = curr['slug'].upper()
            price = curr['price']
            print(slug)
            if slug == 'USD':
                self.set_usd_price(price)
            if slug in desired_ones:
                res += '🔸 %s: %s تومان\n\n' % (self.dict_persian_names[slug], price)
        return self.signed_message(res)

    # --------- Currency -----------
    def send_request(self):
        response = super(SourceArena, self).send_request()
        return response["data"] if 'data' in response else []

