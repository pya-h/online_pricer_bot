from datetime import datetime
from random import randint
from api.base import BaseAPIService
from tools.mathematix import tz_today, from_now_time_diff
from json import dumps as jsonify
from typing import Dict


class TetherService(BaseAPIService):
    TetherSymbol = 'USDT'

    def __init__(self, url: str, token: str, source: str) -> None:
        self.token = token
        super(TetherService, self).__init__(url=url, source=source)
        self.headers = {'Authorization': None}
        self.recent_response: float | None = None
        self.recent_total_response: dict = {}
        self.no_response_counts: int = 0
        self.last_guess_date: datetime = tz_today()
        self.usd_recent_guess: int = 0

    def mid(self) -> float | None:
        pass

    async def get(self):
        pass

    def summary(self, api_data: Dict[str, str | bool | float | int], mid_price_key: str) -> str:
        tether = api_data
        tether[mid_price_key] = self.mid()
        tether['USD'] = self.usd_recent_guess
        return jsonify(tether)

    def time_for_next_guess(self) -> int:
        if not self.recent_response:
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
        self.usd_recent_guess = 10 * ((self.recent_response - diff) // 10)
        return self.usd_recent_guess


class AbanTetherService(TetherService):
    def __init__(self, token: str) -> None:
        super(AbanTetherService, self).__init__(
            url=f'https://abantether.com/api/v1/otc/coin-price?coin={AbanTetherService.TetherSymbol}',
            token=token, source="Abantether.com")
        self.headers = {'Authorization': f'Token {self.token}'}

    def mid(self) -> float | None:
        if self.recent_total_response and AbanTetherService.TetherSymbol in self.recent_total_response:
            value = self.recent_total_response[AbanTetherService.TetherSymbol]
            mid = (float(value['irtPriceBuy']) + float(value['irtPriceSell'])) / 2.0
            self.recent_response = mid
            self.no_response_counts = 0
            return mid
        return None

    async def get(self):
        self.recent_total_response = await self.get_request(headers=self.headers)
        self.no_response_counts += 1
        self.recent_response = None
        if self.recent_total_response and AbanTetherService.TetherSymbol in self.recent_total_response:
            value = self.recent_total_response[AbanTetherService.TetherSymbol]
            self.recent_response = value['irtPriceBuy']
            self.no_response_counts = 0
            return self.recent_response
        return None

    def summary(self) -> str:
        return super(AbanTetherService, self).summary(self.recent_total_response[self.TetherSymbol], 'irtMidPoint')


class NobitexService(TetherService):
    TomanSymbol = "IRT"

    def __init__(self, token: str) -> None:
        super(NobitexService, self).__init__(url='https://api.nobitex.ir/market/stats', token=token,
                                             source="Abantether.com")
        self.headers = {'Authorization': f'Bearer {self.token}'}

    def mid(self) -> float | None:
        if self.recent_total_response and AbanTetherService.TetherSymbol in self.recent_total_response:
            value = self.recent_total_response[AbanTetherService.TetherSymbol]
            mid = (float(value['bestBuy']) + float(value['bestSell'])) / 2.0
            self.recent_response = mid
            self.no_response_counts = 0
            return mid
        return None

    async def get(self):
        self.no_response_counts += 1
        self.recent_total_response = await self.post_request(headers=self.headers, payload={
            "srcCurrency": self.TetherSymbol,
            "dstCurrency": self.TomanSymbol
        })
        result = self.recent_total_response.data
        if self.recent_total_response.OK or not result or 'status' not in result or ['status'].lower() != 'ok':
            raise Exception("Couldn't retrieve tether from nobitex")
        print(result)
        if 'global' in self.recent_total_response:
            del self.recent_total_response['global']
        self.no_response_counts = 0
        self.recent_response = None
        if self.recent_total_response and self.TetherSymbol in self.recent_total_response:
            value = self.recent_total_response["stats"][f"{self.TetherSymbol}-{self.TomanSymbol}"]
            self.recent_response = value['bestBuy']
            self.no_response_counts = 0
            return self.recent_response
        return None

    def summary(self) -> str:
        return super(AbanTetherService, self).summary(self.recent_total_response[self.TetherSymbol], 'bestPriceMid')
