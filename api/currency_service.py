from api.base import *
import json
from tools.exceptions import InvalidInputException
from api.tether_service import AbanTetherService, NobitexService
from tools.manuwriter import log
from tools.mathematix import persianify
from tools.exceptions import NoLatestDataException
from typing import Union


def get_gold_names(filename: str):
    gold_names_fa = "{}"
    try:
        json_file = open(f"./api/data/{filename}.json", "r")
        gold_names_fa = json_file.read()
        json_file.close()
    except Exception as e:
        log("Cannot get currency names", exception=e, category_name="Currency")
    return json.loads(gold_names_fa)


def get_persian_currency_names():
    currency_names_fa = "{}"
    gold_names_fa = "{}"
    try:
        json_file = open("./api/data/national-currencies.fa.json", "r")
        currency_names_fa = json_file.read()
        json_file.close()
        json_file = open("./api/data/golds.fa.json", "r")
        gold_names_fa = json_file.read()
        json_file.close()
    except Exception as e:
        log("Cannot get currency names", exception=e, category_name="Currency")

    return json.loads(currency_names_fa), json.loads(gold_names_fa)


def get_shortcuts():
    shortcut_names_fa = "{}"
    try:
        json_file = open("./api/data/fiat-shortcut.fa.json", "r")
        shortcut_names_fa = json_file.read()
        json_file.close()
    except Exception as e:
        log("Cannot get currency names", exception=e, category_name="Currency")

    return json.loads(shortcut_names_fa)


class CurrencyService(APIService):
    defaultTetherInTomans = 61300
    defaultUsdInTomans = 61000

    def __init__(self, url: str, source: str, cache_file_name: str, token: str, tether_service_token: str) -> None:
        super(CurrencyService, self).__init__(url=url, source=source, cache_file_name=cache_file_name)
        self.token = token
        self.tether_service_token = tether_service_token

        if not self.usdInTomans:
            self.usdInTomans = self.defaultUsdInTomans
        if not self.tetherInTomans:
            self.tetherInTomans = self.defaultTetherInTomans


class GoldService(BaseAPIService):
    entitiesInDollars = ("ONS", "ONSNOGHRE", "PALA", "ONSPALA", "OIL")
    goldsInPersian = None

    def __init__(self, token: str) -> None:
        super().__init__(
            url=f"https://sourcearena.ir/api/?token={token}&currency",
            source="GoldService.ir",
            cache_file_name="SourceArenaGolds.json",
        )
        self.token = token
        if not GoldService.goldsInPersian:
            GoldService.goldsInPersian = get_gold_names("golds.sa.fa")

    async def append_gold_prices(self, api_data: dict):
        self.latest_data = await self.get_request()  # update latest
        for curr in self.latest_data:
            slug = curr["slug"].upper()

            if slug in GoldService.goldsInPersian:
                # repetitive code OR using multiple conditions (?)
                if slug not in GoldService.entitiesInDollars:
                    api_data[slug.lower()] = {
                        "value": float(curr["price"]) / 10,
                    }
                else:
                    api_data[slug.lower()] = {"value": float(curr["price"]), "usd": True}

    # --------- Currency -----------
    async def get_request(self):
        response = await super(GoldService, self).get_request()
        return response["data"] if "data" in response else []

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
    persianShortcuts: Dict[str, str] | None = None
    currenciesInPersian = None
    nationalCurrenciesInPersian = None
    goldsInPersian = None
    maxExtraServicesFailure = 5

    @staticmethod
    def getDefaultCurrencies():
        return set(NavasanService.defaults)

    def __init__(self, token: str, nobitex_tether_service_token: str = None, aban_tether_service_token: str = None) -> None:
        self.tether_service = (
            NobitexService(nobitex_tether_service_token)
            if nobitex_tether_service_token
            else AbanTetherService(aban_tether_service_token)
        )

        super().__init__(
            url=f"https://sourcearena.ir/api/?token={token}&currency&v2",
            source="Navasan.ir",
            cache_file_name="Navasan.json",
            tether_service_token=self.tether_service.token,
            token=token,
        )

        self.gold_service: GoldService = GoldService(self.token)
        if (
            not NavasanService.nationalCurrenciesInPersian
            or not NavasanService.goldsInPersian
            or not NavasanService.currenciesInPersian
            or not NavasanService.persianShortcuts
        ):
            NavasanService.loadPersianNames()

    def get_desired_ones(self, selection: set):
        return selection or set(NavasanService.defaults)

    @staticmethod
    def find(word: str):
        for slug in NavasanService.currenciesInPersian:
            if slug == word or NavasanService.currenciesInPersian[slug] == word:
                return slug
        return None

    @staticmethod
    def loadPersianNames():
        NavasanService.nationalCurrenciesInPersian, NavasanService.goldsInPersian = get_persian_currency_names()
        NavasanService.goldsInPersian = dict(GoldService.goldsInPersian, **NavasanService.goldsInPersian)
        NavasanService.currenciesInPersian = dict(NavasanService.nationalCurrenciesInPersian, **NavasanService.goldsInPersian)
        NavasanService.persianShortcuts = get_shortcuts()

    @staticmethod
    def getPersianName(symbol: str) -> str:
        if NavasanService.currenciesInPersian is None or not NavasanService.currenciesInPersian:
            NavasanService.loadPersianNames()
        if symbol not in NavasanService.currenciesInPersian:
            raise InvalidInputException("Currency Symbol/Name!")
        return NavasanService.currenciesInPersian[symbol]

    def extract_api_response(self, desired_ones: list = None) -> str:
        desired_ones = self.get_desired_ones(desired_ones)
        res_curr = ""
        res_gold = ""

        for slug in desired_ones:
            row = self.get_price_description_row(slug.lower())
            if slug in NavasanService.nationalCurrenciesInPersian:
                res_curr += f"🔸 {row}\n"
            else:
                res_gold += f"🔸 {row}\n"
        return res_curr, res_gold

    async def update_services(self):
        try:
            await self.tether_service.get()
        except Exception as ex:
            log("USDT(Tether) Update Failure", ex, "USD_T")

    # --------- Currency -----------
    async def get_request(self):
        await self.update_services()
        response = await super(NavasanService, self).get_request(no_cache=True)
        return response.data

    async def get(self, desired_ones: set = None) -> str:
        self.latest_data = await self.get_request()  # update latest
        try:
            await self.gold_service.append_gold_prices(self.latest_data)
        except Exception as ex:
            log("Gold Price Update Failure", ex, "SourceArenaGolds")

        if self.tether_service.recent_value:
            self.set_tether_tomans(self.tether_service.recent_value)
        try:
            self.set_usd_price(self.latest_data["usd"]["value"])
        except Exception as ex:
            log("USD(Dollar) Update Failure", ex, "USD_T")

        self.latest_data[self.tomanSymbol.lower()] = {"value": 1 / self.usdInTomans}
        self.cache_data(json.dumps(self.latest_data))
        return self.extract_api_response(desired_ones)

    def load_cache(self) -> list | dict:
        try:
            self.latest_data = super(NavasanService, self).load_cache()["data"]
        except:
            self.latest_data = []
        return self.latest_data

    def irt_to_usd(self, irt_price: float | int) -> float | int:
        return irt_price / self.usdInTomans

    def irt_to_currencies(self, absolute_amount: float | int, source_unit_slug: str, currencies: set = None) -> Tuple[str, str]:
        currencies = self.get_desired_ones(currencies)
        res_gold, res_fiat = "", ""

        for slug in currencies:
            if slug == source_unit_slug:
                continue
            slug_equalized_price = (
                absolute_amount / float(self.latest_data[slug.lower()]["value"])
                if slug != self.tomanSymbol
                else absolute_amount
            )
            slug_equalized_price = mathematix.persianify(mathematix.cut_and_separate(slug_equalized_price))
            if slug in NavasanService.nationalCurrenciesInPersian:
                res_fiat += f"🔸 {slug_equalized_price} {NavasanService.currenciesInPersian[slug]}\n"
            else:
                res_gold += f"🔸 {slug_equalized_price} {NavasanService.currenciesInPersian[slug]}\n"

        return res_fiat, res_gold

    def equalize(
        self, source_unit_symbol: str, amount: float | int, target_currencies: list = None
    ) -> Union[str, float | int, float | int]:
        """This function gets an amount param, alongside with a source_unit_symbol [and obviously with the users desired coins]
        and it returns a text string, that in each row of that, shows that amount equivalent in another currency unit."""
        # First check the required data is prepared
        if not self.latest_data:
            raise NoLatestDataException("use for equalizing!")
        if source_unit_symbol not in NavasanService.currenciesInPersian:
            raise InvalidInputException("Currency/Gold symbol!")

        # first row is the equivalent price in USD(the price unit selected by the bot configs.)
        try:
            absolute_amount: float = amount * float(self.latest_data[source_unit_symbol.lower()]["value"])
        except:
            raise ValueError(f"{source_unit_symbol} has not been received from the API.")
        res_fiat, res_gold = self.irt_to_currencies(absolute_amount, source_unit_symbol, target_currencies) if target_currencies else (None, None)
        return (
            res_fiat,
            res_gold,
            self.irt_to_usd(absolute_amount),
            absolute_amount,
        )

    def get_single_price(self, currency_symbol: str, price_unit: str = "usd"):
        curr = currency_symbol.lower()
        price_unit = price_unit.lower()
        if (
            not self.latest_data
            or not isinstance(self.latest_data, dict)
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

    def get_price_description_row(self, symbol: str) -> str:
        try:
            price: float
            currency_data: Dict[str, float | int | bool | str]
            currency_data = self.latest_data[symbol.lower()]
            price = float(currency_data["value"])
            toman: float = 0.0
            usd: float | None = None
            if "usd" not in currency_data or not currency_data["usd"]:
                toman, _ = self.rounded_prices(price, False)
            else:
                usd, toman = self.rounded_prices(price)

            toman = persianify(toman)
            if price < 0:
                toman = f"{toman[1:]}-"
            return f"{NavasanService.currenciesInPersian[symbol.upper()]}: {toman} تومان" + (f" / {usd}$" if usd else "")
        except:
            pass
        return f"{NavasanService.currenciesInPersian[symbol.upper()]}: ❗️ قیمت دریافت نشد"
