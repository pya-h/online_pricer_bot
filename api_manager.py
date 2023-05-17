import requests, json

# Base class for all api managers

class APIManager:

    UsdInTomans = 52000
    def __init__(self, url, source, dict_persian_names, max_desired_selection = 5, params=None) -> None:
        self.URL = url
        self.Source = source
        self.params = params
        self.latest_data = []
        self.dict_persian_names = dict_persian_names
        self.MAX_DESIRED_SELECTION = max_desired_selection

    def set_usd_price(self, value):
        APIManager.UsdInTomans = value

    def set_params(self, pms):
        self.params = pms

    def get_desired_ones(self, desired_ones):
        if not desired_ones:
            desired_ones = list(self.dict_persian_names.keys())[:self.MAX_DESIRED_SELECTION]
        return desired_ones

    def extract_api_response(self, desired_ones=None) -> str: pass

    def signed_message(self, message) -> str:
        return f"{message}\n\nمنبع: {self.Source}"

    def get(self, desired_ones=None) -> str:
        self.latest_data = self.send_request() # update latest
        return self.extract_api_response(desired_ones)  # then make message

    def get_latest(self, desired_ones=None) -> str:
        return self.extract_api_response(desired_ones)

    def send_request(self):
        response = requests.get(self.URL, json=self.params)
        data = json.loads(response.text)
        return data

