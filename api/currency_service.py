import asyncio

from api.base import *
import json
from tools.exceptions import InvalidInputException
from api.tether_service import AbanTetherService, NobitexService
from tools.manuwriter import log, load_json
from tools.mathematix import persianify
from tools.exceptions import NoLatestDataException
from typing import Union, List, Tuple, Any, override


def get_gold_names(filename: str):
    try:
        return load_json(filename, "./api/data")
    except Exception as e:
        log("Cannot get currency names", exception=e, category_name="SETUP")


def get_persian_currency_names():
    try:
        currency_names_fa = load_json("national-currencies.fa", "./api/data")
        gold_names_fa = load_json("golds.fa", "./api/data")
        gold_names_en = load_json("golds.en", "./api/data")
        return currency_names_fa, gold_names_fa, gold_names_en
    except Exception as e:
        log("Cannot get currency names", exception=e, category_name="SETUP")

    return None, None, None


def get_shortcuts():
    try:
        return load_json("fiat-shortcut.fa", "./api/data")
    except Exception as e:
        log("Cannot get currency names", exception=e, category_name="SETUP")


class CurrencyService(APIService):
    defaultTetherInTomans = 61300
    defaultUsdInTomans = 61000

    def __init__(
        self,
        url: str,
        source: str,
        cache_file_name: str,
        token: str,
        tether_service_token: str,
    ) -> None:
        super(CurrencyService, self).__init__(url=url, source=source, cache_file_name=cache_file_name)
        self.token = token
        self.tether_service_token = tether_service_token
        self.latest_data = []
        if not self.usdInTomans:
            self.usdInTomans = self.defaultUsdInTomans
        if not self.tetherInTomans:
            self.tetherInTomans = self.defaultTetherInTomans


class GoldService(BaseAPIService):
    entitiesInDollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
    goldsInPersian = None
    goldsInEnglish = None

    def __init__(self, token: str) -> None:
        super().__init__(
            url=f"https://apis.sourcearena.ir/api/?token={token}&currency",
            source="GoldService.ir",
            cache_file_name="SourceArenaGolds.json",
        )
        self.token = token
        if not GoldService.goldsInPersian:
            GoldService.goldsInPersian = get_gold_names("golds.sa.fa")
        if not GoldService.goldsInEnglish:
            GoldService.goldsInEnglish = get_gold_names("golds.sa.en")

    async def append_gold_prices(self, api_data: dict):
        try:
            self.latest_data = await self.get_request()
        except Exception as x:
            log("SourceArena Failed Fetching Extra Gold Prices. App will use recent prices.", x, "SourceArena")

        for curr in self.latest_data:
            slug = curr["slug"].upper()

            if slug in GoldService.goldsInPersian:
                if slug not in GoldService.entitiesInDollars:
                    api_data[slug.lower()] = {
                        "value": float(curr["price"]) / 10,
                    }
                else:
                    api_data[slug.lower()] = {
                        "value": float(curr["price"]),
                        "usd": True,
                    }

    @override
    async def get_request(self, headers: dict = None, no_cache: bool = True):
        response = await super(GoldService, self).get_request(headers, no_cache)
        if "data" not in response:
            raise Exception("No data provided by endpoint.")
        return response["data"]

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(GoldService, self).load_cache()["data"]
        except:
            self.latest_data = []
        return self.latest_data


class NavasanService(CurrencyService):
    defaults = (
        "USD",
        "EUR",
        "AED",
        "GBP",
        "TRY",
        "ONS",
        "TALA_18",
        "TALA_MESGHAL",
        "SEKE_EMAMI",
        "SEKE_GERAMI",
    )
    userDefaults = (
        "USD",
        "EUR",
        "TALA_18",
        "SEKE_EMAMI",
    )
    persianShortcuts: Dict[str, str] | None = None
    currenciesInPersian = None
    nationalCurrenciesInPersian = None
    goldsInPersian = None
    goldsInEnglish = None
    majorPriceUnits: Dict[str, Dict[str, str]] = None

    @staticmethod
    def getDefaultCurrencies():
        return list(NavasanService.defaults)

    @staticmethod
    def getUserDefaultCurrencies():
        return list(NavasanService.userDefaults)

    def __init__(
        self,
        token: str,
        nobitex_tether_service_token: str,
        aban_tether_service_token: str = None,
    ) -> None:
        self.tether_service = NobitexService(nobitex_tether_service_token)
        self.alternate_tether_service = AbanTetherService(aban_tether_service_token) if aban_tether_service_token else None
        super().__init__(
            url=f"https://apis.sourcearena.ir/api/?token={token}&currency&v2",
            source="Navasan",
            cache_file_name="Navasan.json",
            tether_service_token=self.tether_service.token,
            token=token,
        )
        self.gold_service: GoldService = GoldService(self.token)
        self.pre_latest_data: dict | None = None

        if (
            not NavasanService.currenciesInPersian
            or not NavasanService.nationalCurrenciesInPersian
            or not NavasanService.currenciesInPersian
            or not NavasanService.goldsInPersian
            or not NavasanService.goldsInEnglish
            or not NavasanService.persianShortcuts
        ):
            NavasanService.loadPersianNames()

    def get_desired_ones(self, selection: List[str] | None) -> List[str]:
        return selection or NavasanService.defaults

    @staticmethod
    def find(word: str):
        for slug in NavasanService.currenciesInPersian:
            if slug == word or NavasanService.currenciesInPersian[slug] == word:
                return slug
        return None

    @staticmethod
    def loadPersianNames():
        (
            NavasanService.nationalCurrenciesInPersian,
            NavasanService.goldsInPersian,
            NavasanService.goldsInEnglish,
        ) = get_persian_currency_names()
        NavasanService.goldsInPersian = dict(GoldService.goldsInPersian, **NavasanService.goldsInPersian)
        NavasanService.currenciesInPersian = dict(
            NavasanService.nationalCurrenciesInPersian, **NavasanService.goldsInPersian
        )
        NavasanService.goldsInEnglish = dict(GoldService.goldsInEnglish, **NavasanService.goldsInEnglish)
        NavasanService.persianShortcuts = get_shortcuts()
        NavasanService.majorPriceUnits = {
            "irt": {"fa": NavasanService.currenciesInPersian["IRT"], "FA": "IRT", "en": "IRT"},
            "usd": {"fa": NavasanService.currenciesInPersian["USD"], "FA": "USD", "en": "USD"},
        }

    @staticmethod
    def getPersianName(symbol: str) -> str:
        if not NavasanService.currenciesInPersian:
            NavasanService.loadPersianNames()
        if symbol not in NavasanService.currenciesInPersian:
            raise InvalidInputException(f"Currency Symbol/Name: {symbol}!")
        return NavasanService.currenciesInPersian[symbol]

    def extract_api_response(
        self,
        desired_ones: List[str] = None,
        language: str = "fa",
        no_price_message: str | None = None,
    ) -> Tuple[str, str]:
        desired_ones = self.get_desired_ones(desired_ones)
        res_curr = ""
        res_gold = ""

        for slug in desired_ones:
            row = self.get_price_description_row(slug.lower(), language, no_price_message)
            if slug not in NavasanService.goldsInPersian:
                res_curr += f"{row}\n"
            else:
                res_gold += f"{row}\n"
        return res_curr, res_gold

    # --------- Currency -----------
    async def get_request(self, _: dict = None, __: bool = False):
        _, response = await asyncio.gather(
            self.tether_service.get(),
            super(NavasanService, self).get_request()
        )

        return response

    async def select_best_tether_price(self):
        try:
            if self.tether_service.recent_value and self.tether_service.no_response_counts < 3:
                self.set_tether_tomans(self.tether_service.recent_value)
                return

            await self.alternate_tether_service.get()
            if self.alternate_tether_service.recent_value and self.alternate_tether_service.no_response_counts < 3:
                self.set_tether_tomans(self.alternate_tether_service.recent_value)
                return

        except Exception as x:
            log('Failed updating USDT-IRT price through tether services. Navasan prices will be used.', x, category_name='TetherService')

        self.set_tether_tomans(self.latest_data["usd_usdt"]["value"])

    async def get(
        self,
        desired_ones: List[str] = None,
        language: str = "fa",
        no_price_message: str | None = None,
    ) -> Tuple[str, str]:
        try:
            new_data = await self.get_request()
            self.pre_latest_data = self.latest_data # only update pre_latest when the api call was ok
            self.latest_data = new_data
        except Exception as ex:
            log('Navasan API Error:', ex, 'Navasan')

        if not self.latest_data:
            return '', ''  # TODO: Think on whats the best course of action?

        await asyncio.gather(
            self.gold_service.append_gold_prices(self.latest_data),
            self.select_best_tether_price(),
        )

        try:
            self.set_usd_price(self.latest_data["usd"]["value"])
        except Exception as ex:
            log("Update USD Price Error", ex, "Navasan")

        self.latest_data[self.tomanSymbol.lower()] = {"value": 1 / self.usdInTomans}
        self.cache_data(json.dumps(self.latest_data))
        return self.extract_api_response(desired_ones, language, no_price_message)

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(NavasanService, self).load_cache()["data"]
        except:
            self.latest_data = []
        return self.latest_data

    def irt_to_usd(self, irt_price: float | int) -> float | int:
        return irt_price / self.usdInTomans

    def irt_to_currencies(
        self,
        absolute_irt: float | int,
        source_unit_slug: str,
        currencies: List[str] | None = None,
        language: str = "fa",
        absolute_usd: float | int = None,
    ) -> Tuple[str, str]:
        currencies = self.get_desired_ones(currencies)
        res_gold, res_fiat = "", ""
        for slug in currencies:
            if slug == source_unit_slug:
                continue
            slug_equalized_price = absolute_irt if slug == self.tomanSymbol \
                else (absolute_irt / float(self.latest_data[slug.lower()]["value"])
                    if (slug != self.dollarSymbol and source_unit_slug != self.tetherSymbol) or not absolute_usd
                        else absolute_usd)

            slug_equalized_price = mathematix.cut_and_separate(slug_equalized_price)
            if slug not in NavasanService.goldsInPersian:
                if language != "fa":
                    res_fiat += f"🔸 {slug_equalized_price} {slug}\n"
                else:
                    slug_equalized_price = mathematix.persianify(slug_equalized_price)
                    res_fiat += f"🔸 {slug_equalized_price} {NavasanService.nationalCurrenciesInPersian[slug]}\n"
            else:
                if language != "fa":
                    res_gold += f"🔸 {slug_equalized_price} {NavasanService.goldsInEnglish[slug]}\n"
                else:
                    slug_equalized_price = mathematix.persianify(slug_equalized_price)
                    res_gold += f"🔸 {slug_equalized_price} {NavasanService.goldsInPersian[slug]}\n"
        return res_fiat, res_gold

    def equalize(
        self,
        source_unit_symbol: str,
        amount: float | int,
        target_currencies: List[str] | None = None,
        language: str = "fa",
    ) -> Tuple[Any, Any, float | int, float]:
        """This function gets an amount param, alongside with a source_unit_symbol [and obviously with the users desired coins]
        and it returns a text string, that in each row of that, shows that amount equivalent in another currency unit.
        """
        # First check the required data is prepared
        if not self.latest_data:
            raise NoLatestDataException("use for equalizing!")
        if source_unit_symbol not in NavasanService.currenciesInPersian:
            raise InvalidInputException(f"Currency/Gold symbol: {source_unit_symbol}!")

        # first row is the equivalent price in USD(the price unit selected by the bot configs.)
        try:
            absolute_amount: float = amount * (
                float(self.latest_data[source_unit_symbol.lower()]["value"])
                if source_unit_symbol != self.tomanSymbol
                else 1
            )
        except:
            raise ValueError(f"{source_unit_symbol} has not been received from the API.")
        res_fiat, res_gold = (
            self.irt_to_currencies(absolute_amount, source_unit_symbol, target_currencies, language)
            if target_currencies
            else (None, None)
        )
        return (
            res_fiat,
            res_gold,
            self.irt_to_usd(absolute_amount) if source_unit_symbol != self.dollarSymbol else amount,
            absolute_amount,
        )

    def get_single_price(self, currency_symbol: str, price_unit: str = "usd"):
        curr = currency_symbol.lower()
        price_unit = price_unit.lower()
        if (
            not isinstance(self.latest_data, dict)
            or not curr in self.latest_data
            or not "value" in self.latest_data[curr]
        ):
            return None
        if curr == self.dollarSymbol:
            return self.usdInTomans if price_unit != "usd" else 1

        currency_data = self.latest_data[curr]

        if "usd" not in currency_data or not currency_data["usd"]:
            toman = currency_data["value"]
            return toman if price_unit != "usd" else self.irt_to_usd(toman)

        # if price is in $
        usd_price = currency_data["value"]
        return self.to_irt_exact(usd_price) if price_unit != "usd" else usd_price

    @staticmethod
    def getEnglishTitle(symbol: str) -> str:
        return symbol if symbol not in NavasanService.goldsInEnglish else NavasanService.goldsInEnglish[symbol]

    def get_price_description_row(self, symbol: str, language: str = "fa", no_price_message: str | None = None) -> str:
        symbol_up = symbol.upper()
        try:
            if (sym_lower := symbol.lower()) not in self.latest_data:
                raise ValueError(f"{sym_lower} not found in Navasan response data!")
            currency_data = self.latest_data[sym_lower]
            price = float(currency_data["value"])

            try:
                previous_price = float(self.pre_latest_data[sym_lower]['value'])
            except:
                previous_price = price

            usd: float | None = None
            if "usd" not in currency_data or not currency_data["usd"]:
                toman, _ = self.rounded_prices(price, False)
            else:
                usd, toman = self.rounded_prices(price)
            if language != "fa":
                return f"{self.getTokenState(price, previous_price)} {NavasanService.getEnglishTitle(symbol_up)}: {toman} {self.tomanSymbol}" + (
                    f" / {usd}$" if usd else ""
                )
            toman = persianify(toman)
            if price < 0:
                toman = f"{toman[1:]}-"
            return f"{self.getTokenState(price, previous_price)} {NavasanService.currenciesInPersian[symbol_up]}: {toman} تومان" + (
                f" / {usd}$" if usd else ""
            )
        except Exception as x:
            log("Symbol not found!", x, "Navasan")
        try:
            return (
                f"🔸 {NavasanService.getEnglishTitle(symbol_up) if language != 'fa' else NavasanService.goldsInPersian[symbol_up]}: "
                + (no_price_message or "❗️")
            )
        except:
            pass
        return f"🔸 {symbol}: " + (no_price_message or "❗️")
