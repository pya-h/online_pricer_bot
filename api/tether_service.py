from datetime import datetime
from random import randint
from api.base import BaseAPIService
from tools.mathematix import tz_today, from_now_time_diff
from json import dumps as jsonify
from typing import Dict, override
from tools.manuwriter import log


class TetherService(BaseAPIService):
    def __init__(self, url: str, token: str, source: str, cache_name: str | None = None) -> None:
        self.token = token
        super(TetherService, self).__init__(url=url, source=source, cache_file_name=cache_name)
        self.headers = {"Authorization": None}
        self.recent_value: float | None = None
        self.recent_response: dict = {}
        self.no_response_counts: int = 0
        self.last_guess_date: datetime = tz_today()
        self.usd_recent_guess: int = 0

    @property
    def mid(self) -> float:
        return 0.0

    async def get(self):
        pass

    def data_summary(self, api_data: Dict[str, str | bool | float | int], mid_price_key: str) -> str:
        tether = api_data
        tether[mid_price_key] = self.mid
        tether["USD"] = self.usd_recent_guess
        return jsonify(tether)

    def time_for_next_guess(self) -> int:
        if not self.recent_value:
            return False
        if not self.usd_recent_guess:
            return True
        diff, now = from_now_time_diff(self.last_guess_date)
        if diff < 60:
            return False
        if 10 <= now.hour < 22:
            self.last_guess_date = now
            return True
        return False

    def guess_dollar_price(self, guess_range: int = 100) -> int | float:
        if not self.time_for_next_guess():
            return self.usd_recent_guess
        diff = randint(1, guess_range)
        self.usd_recent_guess = 10 * ((self.recent_value - diff) // 10)
        return self.usd_recent_guess


class AbanTetherService(TetherService):

    def __init__(self, token: str) -> None:
        super(AbanTetherService, self).__init__(
            url=f"https://abantether.com/api/v1/otc/coin-price?coin={AbanTetherService.tetherSymbol}",
            token=token,
            source="Abantether.com",
            cache_name="AbanTether.json",
        )
        self.headers = {"Authorization": f"Token {self.token}"}

    @override
    @property
    def mid(self) -> float:
        if self.recent_response and AbanTetherService.tetherSymbol in self.recent_response:
            value = self.recent_response[AbanTetherService.tetherSymbol]
            self.recent_value = (float(value["irtPriceBuy"]) + float(value["irtPriceSell"])) / 2.0
            return self.recent_value
        return 0.0

    @override
    async def get(self):
        try:
            self.recent_response = await self.get_request(headers=self.headers)
            self.no_response_counts = 0
        except Exception as x:
            self.no_response_counts += 1
            log('AbanTether API Failure', x, category_name='AbanTether')
        self.recent_value = self.mid
        return self.recent_value

    def summary(self) -> str:
        return self.data_summary(self.recent_response[self.tetherSymbol], "irtMidPoint")


class NobitexService(TetherService):
    tetherFieldName = f'{TetherService.tetherSymbol}-{TetherService.tomanSymbol}'

    def __init__(self, token: str) -> None:
        super(NobitexService, self).__init__(
            url="https://api.nobitex.ir/market/stats", token=token, source="Nobitex", cache_name="Nobitex.json"
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @override
    @property
    def mid(self) -> float:
        if self.recent_response and NobitexService.tetherFieldName in self.recent_response:
            value = self.recent_response[NobitexService.tetherFieldName]
            self.recent_value = (float(value["bestBuy"]) + float(value["bestSell"])) / 2.0
            return self.recent_value
        print(self.recent_value)
        return 0.0

    async def fetch_prices(self):
        response = await self.post_request(
            headers=self.headers, payload={"srcCurrency": self.tetherSymbol, "dstCurrency": self.tomanSymbol}
        )
        if 'status' in response and response['status'].lower() == 'ok':
            return response['stats']
        return None

    @override
    async def get(self):
        try:
            self.recent_response = await self.fetch_prices()

            value = self.recent_response[NobitexService.tetherFieldName]
            value["bestBuy"] = float(value["bestBuy"]) / 10.0
            value["bestSell"] = float(value["bestSell"]) / 10.0
            self.no_response_counts = 0
        except Exception as x:
            self.no_response_counts += 1
            log('Nobitex API Failure', x, category_name='Nobitex')
        self.recent_value = self.mid
        return self.recent_value

    def summary(self) -> str:
        return self.data_summary(self.recent_response[NobitexService.tetherFieldName], "bestPriceMid")
