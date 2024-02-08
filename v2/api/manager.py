import requests, json
from tools import mathematix, manuwriter

CACHE_FOLDER = 'api.cache'

class BaseAPIManager:
    '''The very Base class for all api managers'''
    def __init__(self, url: str, source: str, timeout: int=10, params: dict=None, cache_file_name: str = None) -> None:
        self.URL: str = url
        self.Source: str = source
        self.timeout: int = timeout
        self.params: dict = params
        self.cache_file_name: str = cache_file_name

    def cache_data(self, data: str) -> None:
        cache_folder_path = CACHE_FOLDER
        try:
            manuwriter.prepare_folder(cache_folder_path)
        except OSError as e:
            manuwriter.log('api-cache folder creation failed!', e, 'cache')
            cache_folder_path = ''  # if can not create the folder, well just save it in cwd

        json_cache_file = open(f'./{cache_folder_path}/{self.cache_file_name}', 'w')
        json_cache_file.write(data)
        json_cache_file.close()

    def send_request(self, headers: dict = None):
        data = None
        try:
            response = requests.get(self.URL, timeout=self.timeout, headers=headers, json=self.params)
            data = json.loads(response.text)
            if self.cache_file_name and response.status_code == 200 and (response is not None) and (response.text):
                self.cache_data(response.text)

        except requests.exceptions.RequestException as e:
        # Handle any request exceptions
            manuwriter.log("Error occurred while making the request:", e, category_name=self.Source)
        except Exception as e:
            # Handle any other exceptions
            manuwriter.log("An unexpected error occurred:", e, category_name=self.Source)

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

    def get_cache(self, desired_ones: list=None, short_text: bool=True) -> str:
        pass
        # this is for the schedular bot!
        # return self.extract_api_response(desired_ones, short_text=short_text)

    def rounded_prices(self, price, convert=True, tether_as_unit_price=False):
        if convert:
            converted_price = price * (self.TetherInTomans if tether_as_unit_price else self.UsdInTomans)
            return mathematix.cut_and_separate(price), mathematix.cut_and_separate(converted_price)
        return mathematix.cut_and_separate(price), None

    def crypto_description_row(self, name: str, symbol: str, price, short_text=True):
        if symbol != 'USDT':
            rp_usd, rp_toman = self.rounded_prices(price, tether_as_unit_price=True)
        else:
            rp_usd, rp_toman = mathematix.cut_and_separate(price), mathematix.cut_and_separate(self.TetherInTomans)
        rp_toman = mathematix.persianify(rp_toman)
        return f'🔸 {self.dict_persian_names[symbol]}: {rp_toman} تومان / {rp_usd}$\n' if short_text \
            else f'🔸 {name} ({symbol}): {rp_usd}$\n{self.dict_persian_names[symbol]}: {rp_toman} تومان\n'
