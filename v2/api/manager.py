import requests, json
import tools

# Base class for all api managers
class BaseAPIManager:
    def __init__(self, url: str, source: str, timeout=10, params=None) -> None:
        self.URL = url
        self.Source = source
        self.timeout = timeout
        self.params = params
        
    def send_request(self, headers: dict = None):
        response = requests.get(self.URL, timeout=self.timeout, headers=headers, json=self.params)
        data = json.loads(response.text)
        return data


class APIManager(BaseAPIManager):
    UsdInTomans = 52000  # not important, it is just a default value that will be updated at first api get from
    TetherInTomans = 52000
    # sourcearena.ir

    def __init__(self, url: str, source: str, dict_persian_names: dict, max_desired_selection=5, params=None) -> None:
        super(APIManager, self).__init__(url, source, params=params)
        self.latest_data = []
        self.dict_persian_names = dict_persian_names
        self.MAX_DESIRED_SELECTION = max_desired_selection

    @staticmethod
    def set_usd_price(value):
        APIManager.UsdInTomans = value

    @staticmethod
    def set_tether_tomans(value):
        APIManager.TetherInTomans = value

    def get_desired_ones(self, desired_ones: list):
        if not desired_ones:
            desired_ones = list(self.dict_persian_names.keys())[:self.MAX_DESIRED_SELECTION]
        return desired_ones

    def extract_api_response(self, desired_ones: list=None, short_text: bool=True) -> str:
        pass

    def get(self, desired_ones: list=None, short_text: bool=True) -> str:
        self.latest_data = self.send_request()  # update latest
        return self.extract_api_response(desired_ones, short_text=short_text)

    def get_latest(self, desired_ones: list=None, short_text: bool=True) -> str:
        return self.extract_api_response(desired_ones, short_text=short_text)

    def rounded_prices(self, price, convert=True, tether_as_unit_price=False):
        if convert:
            converted_price = price * (self.TetherInTomans if tether_as_unit_price else self.UsdInTomans)
            return tools.cut_and_separate(price), tools.cut_and_separate(converted_price)
        return tools.cut_and_separate(price), None

    def crypto_description_row(self, name: str, symbol: str, price, short_text=True):
        if symbol != 'USDT':
            rp_usd, rp_toman = self.rounded_prices(price, tether_as_unit_price=True)
        else:
            rp_usd, rp_toman = tools.cut_and_separate(price), tools.cut_and_separate(self.TetherInTomans)
        rp_toman = tools.persianify(rp_toman)
        return f'🔸 {self.dict_persian_names[symbol]}: {rp_toman} تومان / {rp_usd}$\n' if short_text \
            else f'🔸 {name} ({symbol}): {rp_usd}$\n{self.dict_persian_names[symbol]}: {rp_toman} تومان\n'
