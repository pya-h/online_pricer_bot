import json
from tools import mathematix, manuwriter
from tools.exceptions import CacheFailureException
import api.api_async as api
from typing import Dict, List, Tuple

CACHE_FOLDER_PATH = "api.cache"
# CACHE_ARCHIVE_FOLDER_PATH = "archives"


class BaseAPIService:
    tetherSymbol = "USDT"
    dollarSymbol = "USD"
    tomanSymbol = "IRT"

    """The very Base class for all api services"""

    def __init__(self, url: str, source: str, timeout: int = 10, params: dict = None, cache_file_name: str = None) -> None:
        self.URL: str = url
        self.Source: str = source
        self.timeout: int = timeout
        self.params: dict = params or dict()
        self.cache_file_name: str = cache_file_name
        self.cache_folder_created: bool = False
        self.latest_data = dict() # Latest loaded cache/API data; This is a helper object for preventing unnecessary Api Call or Cache file read
        # Causing: App enhancement, less APi Calls(For best management of non-free API uses), Less cache file read for improving bot performance and speed and prevention of lags

    def cache_data(self, data: str, custom_file_name: str = None) -> None:
        if not self.cache_folder_created:
            try:
                self.cache_folder_created = manuwriter.prepare_folder(CACHE_FOLDER_PATH)
            except OSError as e:
                manuwriter.log("api-cache folder creation failed!", e, "cache")
                raise CacheFailureException("Cache Folder creation failed!")
        try:
            filename = self.cache_file_name if not custom_file_name else custom_file_name
            manuwriter.fwrite_from_scratch(f"./{CACHE_FOLDER_PATH}/{filename}", data, self.Source)
        except Exception as ex:  # caching is so important for the performance of second bot that :
            # as soon as something goes wrong in caching, the admin must be informed.
            manuwriter.log("Caching failure!", ex, category_name="CACHING")
            raise CacheFailureException(ex)

    async def get_request(self, headers: dict = None, no_cache: bool = True):
        request = api.Request(self.URL, headers=headers, payload=self.params)
        response = await request.get()

        if not response or not response.OK:
            raise Exception(f'GET Failure @ {self.Source}.\nStatus Code: {response.status}\nError: {response.text}')

        if not no_cache and self.cache_file_name and response.text is not None:
            self.cache_data(response.text)

        return response.data

    async def post_request(self, payload: Dict[str, str], headers: dict = None, no_cache: bool = True):
        request = api.Request(self.URL, headers=headers, payload=payload)
        response = await request.post()
        if not response or not response.OK:
            raise Exception(f'POST Failure @ {self.Source}.\nStatus Code: {response.status}\nError: {response.text}')

        if not no_cache and self.cache_file_name and response.text is not None:
            self.cache_data(response.text)
        return response.data

    def load_cache(self) -> list | dict:
        """Read cache and convert it to python dict/list."""
        json_cache_file = open(f"./{CACHE_FOLDER_PATH}/{self.cache_file_name}", "r")
        str_json = json_cache_file.read()
        json_cache_file.close()
        self.latest_data = json.loads(str_json)
        return self.latest_data


class APIService(BaseAPIService):
    usdInTomans = None  # not important, it is just a default value that will be updated at first api get from
    tetherInTomans = None

    def __init__(self, url: str, source: str, params=None, cache_file_name: str = None) -> None:
        super(APIService, self).__init__(url, source, params=params, cache_file_name=cache_file_name)

    @staticmethod
    def set_usd_price(value):
        APIService.usdInTomans = float(value)

    @staticmethod
    def set_tether_tomans(value):
        APIService.tetherInTomans = float(value)

    def get_desired_ones(self, desired_ones: List[str]) -> list:
        pass

    def extract_api_response(self, desired_ones: List[str] = None, language: str = 'fa', no_price_message: str | None = None) -> Tuple[str, str]:
        pass

    async def get(self, desired_ones: List[str] = None, language: str = 'fa', no_price_message: str | None = None) -> Tuple[str, str]:
        self.latest_data = await self.get_request()  # update latest
        return self.extract_api_response(desired_ones, language, no_price_message)

    def get_latest(self, desired_ones: List[str] = None, language: str = 'fa', no_price_message: str | None = None) -> Tuple[str, str]:
        return self.extract_api_response(desired_ones, language, no_price_message)

    def get_desired_cache(self, desired_ones: List[str] = None, force_reload: bool = False) -> Tuple[str, str]:
        """This is for the channel planner bot"""
        try:
            if force_reload or not self.latest_data:
                self.load_cache()
        except Exception as ex:
            if (
                not self.latest_data
            ):  # if there is no cache, and the no latest data either, to prevent crashing, call the api for once
                try:
                    manuwriter.log("couldn't read cache; Using Direct api call to obtain data.", ex, category_name="CACHING")
                    self.latest_data = self.get_request()  # the condition that is happened, may be due to lack of cache file,
                except Exception as fex:
                    manuwriter.log(
                        "Couldn't get cache and API both. There's something seriously wrong!!", fex, category_name="CACHING"
                    )

        return self.extract_api_response(desired_ones)

    def to_irt_exact(self, price: float | int, tether_as_unit_price: bool = False) -> float | int:
        try:
            return price * (self.tetherInTomans if tether_as_unit_price and self.tetherInTomans else self.usdInTomans)
        except:
            pass
        return 0

    def rounded_prices(self, price: float | int, convert: bool = True, tether_as_unit_price: bool = False):
        if convert:
            converted_price = self.to_irt_exact(price, tether_as_unit_price)
            return mathematix.cut_and_separate(price), mathematix.cut_and_separate(converted_price)

        return mathematix.cut_and_separate(price), None

    @staticmethod
    def getTokenState(current_price: float | int, previous_price: float | int) -> str:
        return '🟢' if current_price > previous_price else '🔴' if current_price < previous_price else '⚪️'