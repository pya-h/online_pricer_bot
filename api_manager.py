import requests, json
import tools


# Base class for all api managers

class APIManager:
    UsdInTomans = 52000  # not important, it is just a default value that will be updated at first api get from
    TetherInTomans = 52000
    # sourcearena.ir

    def __init__(self, url, source, dict_persian_names, max_desired_selection=5, icons=None, params=None) -> None:
        self.URL = url
        self.Source = source
        self.params = params
        self.latest_data = []
        self.dict_persian_names = dict_persian_names
        self.MAX_DESIRED_SELECTION = max_desired_selection
        self.icons = icons

    @staticmethod
    def set_usd_price(value):
        APIManager.UsdInTomans = value

    @staticmethod
    def set_tether_tomans(value):
        APIManager.TetherInTomans = value

    def set_params(self, pms):
        self.params = pms

    def get_desired_ones(self, desired_ones):
        if not desired_ones:
            desired_ones = list(self.dict_persian_names.keys())[:self.MAX_DESIRED_SELECTION]
        return desired_ones

    def extract_api_response(self, desired_ones=None, short_text=True) -> str:
        pass

    def get(self, desired_ones=None, short_text=True) -> str:
        self.latest_data = self.send_request()  # update latest
        return self.extract_api_response(desired_ones, short_text=short_text)

    def get_latest(self, desired_ones=None, short_text=False) -> str:
        return self.extract_api_response(desired_ones, short_text=short_text)

    def send_request(self):
        response = requests.get(self.URL, json=self.params, timeout=5)
        data = json.loads(response.text)
        return data

    def rounded_prices(self, price, convert=True, tether_as_unit_price=False):
        if convert:
            converted_price = price * (self.TetherInTomans if tether_as_unit_price else self.UsdInTomans)
            return tools.cut_and_separate(price), tools.cut_and_separate(converted_price)
        return tools.cut_and_separate(price), None

    def crypto_description_row(self, name, symbol, price, short_text=True):
        if symbol != 'USDT':
            rp_usd, rp_toman = self.rounded_prices(price, tether_as_unit_price=True)
        else:
            rp_usd, rp_toman = tools.cut_and_separate(price), tools.cut_and_separate(self.TetherInTomans)
        return f'🔸 {self.dict_persian_names[symbol]}: {rp_toman} تومان / {rp_usd}$\n' if short_text \
            else f'🔸 {name} ({symbol}): {rp_usd}$\n{self.dict_persian_names[symbol]}: {rp_toman} تومان\n'
