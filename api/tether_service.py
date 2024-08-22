from datetime import datetime
from random import randint
from api.base import BaseAPIService
from tools.mathematix import tz_today, from_now_time_diff
from json import dumps as jsonify
from typing import Dict


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

    def mid(self) -> float | None:
        pass

    async def get(self):
        pass

    def summary(self, api_data: Dict[str, str | bool | float | int], mid_price_key: str) -> str:
        tether = api_data
        tether[mid_price_key] = self.mid()
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

    def mid(self) -> float | None:
        if self.recent_response and AbanTetherService.tetherSymbol in self.recent_response:
            value = self.recent_response[AbanTetherService.tetherSymbol]
            mid = (float(value["irtPriceBuy"]) + float(value["irtPriceSell"])) / 2.0
            self.recent_value = mid
            self.no_response_counts = 0
            return mid
        return None

    async def get(self):
        self.recent_response = await self.get_request(headers=self.headers)
        self.no_response_counts += 1
        self.recent_value = None
        if self.recent_response and AbanTetherService.tetherSymbol in self.recent_response:
            raise Exception("Couldn't retrieve tether from AbanTether")
        value = self.recent_response[AbanTetherService.tetherSymbol]
        self.recent_value = value["irtPriceBuy"]
        self.no_response_counts = 0
        return self.recent_value

    def summary(self) -> str:
        return super(AbanTetherService, self).summary(self.recent_response[self.tetherSymbol], "irtMidPoint")


class NobitexService(TetherService):
    def __init__(self, token: str) -> None:
        super(NobitexService, self).__init__(
            url="https://api.nobitex.ir/market/stats", token=token, source="Nobitex.ir", cache_name="Nobitex.json"
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def mid(self) -> float | None:
        if self.recent_response and AbanTetherService.tetherSymbol in self.recent_response:
            value = self.recent_response[AbanTetherService.tetherSymbol]
            mid = (float(value["bestBuy"]) + float(value["bestSell"])) / 2.0
            self.recent_value = mid
            self.no_response_counts = 0
            return mid
        return None

    async def get(self):
        self.no_response_counts += 1
        self.recent_response = await self.post_request(
            headers=self.headers, payload={"srcCurrency": self.tetherSymbol, "dstCurrency": self.tomanSymbol}
        )

        self.recent_value = None

        if not self.recent_response or "status" not in self.recent_response or self.recent_response["status"].lower() != "ok":
            raise Exception("Couldn't retrieve tether from nobitex")
        if "global" in self.recent_response:
            del self.recent_response["global"]
        self.no_response_counts = 0
        value = self.recent_response["stats"][f"{self.tetherSymbol}-{self.tomanSymbol}"]
        value["bestBuy"] = float(value["bestBuy"]) / 10.0
        value["bestSell"] = float(value["bestSell"]) / 10.0
        self.recent_value = value["bestBuy"]
        self.no_response_counts = 0
        return self.recent_value

    def summary(self) -> str:
        return super(AbanTetherService, self).summary(self.recent_response[self.tetherSymbol], "bestPriceMid")
