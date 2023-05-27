import requests, json

# Base class for all api managers

class APIManager:

    UsdInTomans = 52000  # not important, its just a defalt value that will be updated at first api get from sourcearena.ir
    def __init__(self, url, source, dict_persian_names, max_desired_selection = 5, icons=None, params=None) -> None:
        self.URL = url
        self.Source = source
        self.params = params
        self.latest_data = []
        self.dict_persian_names = dict_persian_names
        self.MAX_DESIRED_SELECTION = max_desired_selection
        self.icons = icons

    def set_usd_price(self, value):
        APIManager.UsdInTomans = value

    def set_params(self, pms):
        self.params = pms

    def get_desired_ones(self, desired_ones):
        if not desired_ones:
            desired_ones = list(self.dict_persian_names.keys())[:self.MAX_DESIRED_SELECTION]
        return desired_ones

    def extract_api_response(self, desired_ones=None, short_text=True) -> str: pass

    def get(self, desired_ones=None, short_text=True) -> str:
        self.latest_data = self.send_request() # update latest
        return self.extract_api_response(desired_ones, short_text=short_text)

    def get_latest(self, desired_ones=None) -> str:
        return self.extract_api_response(desired_ones, short_text=False)

    def send_request(self):
        response = requests.get(self.URL, json=self.params)
        data = json.loads(response.text)
        return data

    def rounded_prices(self, price, convert=True):
        rounded_price = round(price, 2)
        converted_rounded_price = round(price * self.UsdInTomans, 2) if convert else None
        if int(rounded_price) == rounded_price:
            rounded_price = int(rounded_price)
        if converted_rounded_price and (converted_rounded_price >= 1000 or int(converted_rounded_price) == converted_rounded_price):
            converted_rounded_price = int(converted_rounded_price)
        return rounded_price, converted_rounded_price

    def crypto_description_row(self, name, symbol, price, short_text=True):
        rp_usd, rp_toman = self.rounded_prices(price)
        return  f'🔸 {self.dict_persian_names[symbol]}: {rp_toman:,} تومان / {rp_usd:,}$\n' if short_text \
            else f'🔸 {name} ({symbol}): {rp_usd:,}$\n{self.dict_persian_names[symbol]}: {rp_toman:,} تومان\n'
