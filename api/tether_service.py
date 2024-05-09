from datetime import datetime
from random import randint
from api.base import BaseAPIService
from tools.mathematix import tz_today, from_now_time_diff
from json import dumps as jsonify


class AbanTether(BaseAPIService):
    TetherSymbol = 'USDT'

    def __init__(self, token: str) -> None:
        self.token = token
        super(AbanTether, self).__init__(
            url=f'https://abantether.com/api/v1/otc/coin-price?coin={AbanTether.TetherSymbol}',
            source="Abantether.com")
        self.headers = {'Authorization': f'Token {self.token}'}
        self.recent_response: float | None = None
        self.recent_total_response: dict = {}
        self.no_response_counts: int = 0
        self.last_guess_date: datetime = tz_today()
        self.usd_recent_guess: int = 0

    def mid(self):
        if self.recent_total_response and AbanTether.TetherSymbol in self.recent_total_response:
            value = self.recent_total_response[AbanTether.TetherSymbol]
            mid = (float(value['irtPriceBuy']) + float(value['irtPriceSell'])) / 2.0
            self.recent_response = mid
            self.no_response_counts = 0
            return mid

        return None

    async def get(self):
        self.recent_total_response = await self.get_request(headers=self.headers)
        self.no_response_counts += 1
        self.recent_response = None
        if self.recent_total_response and AbanTether.TetherSymbol in self.recent_total_response:
            value = self.recent_total_response[AbanTether.TetherSymbol]
            self.recent_response = value['irtPriceBuy']
            self.no_response_counts = 0
            return self.recent_response

        return None

    def summary(self) -> str:
        tether = self.recent_total_response[AbanTether.TetherSymbol]
        tether['irtMidPoint'] = self.mid()
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
