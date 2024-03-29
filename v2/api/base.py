import requests, json
from tools import mathematix, manuwriter
from tools.exceptions import CacheFailureException


CACHE_FOLDER_PATH = 'api.cache'
CACHE_ARCHIVE_FOLDER_PATH = 'archives'

class BaseAPIService:
    TETHER_SYMBOL = 'USDT'
    DOLLAR_SYMBOL = 'USD'

    '''The very Base class for all api services'''
    def __init__(self, url: str, source: str, timeout: int=10, params: dict=None, cache_file_name: str = None) -> None:
        self.URL: str = url
        self.Source: str = source
        self.timeout: int = timeout
        self.params: dict = params
        self.cache_file_name: str = cache_file_name
        self.latest_data = []  # Latest loaded cache/API data; This is a helper object for preventing unnecessary Api Call or Cache file read
        # Causing: App enhancement, less APi Calls(For best managemnt of non-free API uses), Less cache file read for improving bot performance and speed and prevention of lags

    def cache_data(self, data: str) -> None:
        can_be_archived = True
        try:
            _, can_be_archived = manuwriter.prepare_folder(CACHE_FOLDER_PATH, CACHE_ARCHIVE_FOLDER_PATH)
        except OSError as e:
            manuwriter.log('api-cache folder creation failed!', e, 'cache')
            raise CacheFailureException('Cache Folder creation failed!')
        try:
            manuwriter.fwrite_from_scratch(f'./{CACHE_FOLDER_PATH}/{self.cache_file_name}', data, self.Source)
            if can_be_archived:  # as mentioned before, archiving is not crucial; so it will be ignored if its folder can not be created
                # although u should be aware that these errors and failure circumstances are rare
                # Its just for making sure app never crashes
                manuwriter.fwrite_from_scratch('./%s/%s/%s_%s.json' % (CACHE_FOLDER_PATH, CACHE_ARCHIVE_FOLDER_PATH, self.cache_file_name, mathematix.short_timestamp()), data, self.Source)

        except Exception as ex: # caching is so imortant for the performance of second bot that :
            # as soon as something goes wrong in caching, the admin must be informed.
            manuwriter.log('Caching failure!', ex, category_name='FATALITY')
            raise CacheFailureException(ex)

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

    def load_cache(self) -> list|dict:
        '''Read cache and convert it to python dict/list.'''
        json_cache_file = open(f'./{CACHE_FOLDER_PATH}/{self.cache_file_name}', 'r')
        str_json = json_cache_file.read()
        json_cache_file.close()
        self.latest_data = json.loads(str_json)
        return self.latest_data


class APIService(BaseAPIService):
    UsdInTomans = 52000  # not important, it is just a default value that will be updated at first api get from
    TetherInTomans = 52000
    # sourcearena.ir

    def __init__(self, url: str, source: str, max_desired_selection: int=5, params=None, cache_file_name: str = None) -> None:
        super(APIService, self).__init__(url, source, params=params, cache_file_name=cache_file_name)
        self.MAX_DESIRED_SELECTION = max_desired_selection

    @staticmethod
    def set_usd_price(value):
        APIService.UsdInTomans = value

    @staticmethod
    def set_tether_tomans(value):
        APIService.TetherInTomans = value

    def get_desired_ones(self, desired_ones: list):
        pass

    def extract_api_response(self, desired_ones: list=None, short_text: bool=True, optional_api_data:list = None) -> str:
        pass

    def get(self, desired_ones: list=None, short_text: bool=True) -> str:
        self.latest_data = self.send_request()  # update latest
        return self.extract_api_response(desired_ones, short_text=short_text)

    def get_latest(self, desired_ones: list=None, short_text: bool=True) -> str:
        return self.extract_api_response(desired_ones, short_text=short_text)

    def get_desired_cache(self, desired_ones: list=None, short_text: bool=True, force_reload: bool=False) -> str:
        ''' This is for the channel planner bot'''
        try:
            if force_reload or not self.latest_data:
                self.load_cache()
        except Exception as ex:
            if not self.latest_data: # if there is no cache, and the no latest data eigher, to prevent craching, call the api for once
                try:
                    manuwriter.log("Couldnt read cache; Using Direct api call to obtain data.", ex, category_name='CACHE')
                    self.latest_data = self.send_request()  # the condition that is happende, may be due to lack of cache file,
                    # This may be cause when this app is run before oneline_pricer_bot for the first time.
                    # sending a request will make new cache and solve this issue.
                except Exception as fex:
                    manuwriter.log("Couldnt get cache and API both. There\'s something seriously wrong!!", ex, category_name='PLUS_FATALITY')
                    # TODO: send an email or notification or whatever to the admin?

        return self.extract_api_response(desired_ones, short_text=short_text, optional_api_data=self.latest_data)


    def rounded_prices(self, price:float|int, convert: bool=True, tether_as_unit_price: bool=False):
        if convert:
            converted_price = price * (self.TetherInTomans if tether_as_unit_price else self.UsdInTomans)
            return mathematix.cut_and_separate(price), mathematix.cut_and_separate(converted_price)
        return mathematix.cut_and_separate(price), None
