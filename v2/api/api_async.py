from enum import Enum
import aiohttp

class RequestMethod(Enum):
    Get = 1
    Post = 2
    Put = 3
    Patch = 4
    Delete = 5


class Response:
    def __init__(self, response: aiohttp.ClientResponse) -> None:
        self.response = response
        self.raw = None
        self.value = None

    async def read(self):
        self.raw = await self.response.text()
        self.value = await self.response.json() if self.response.content_type == 'application/json' else self.raw
        return self


class Request:

    def __init__(self, url: str, payload: dict = None, header: dict=None, method: RequestMethod=RequestMethod.Get, timeout: float = 5.0) -> None:
        self.__url = url
        self.__payload = payload
        self.__method = method
        self.__headers = header
        if not self.__headers and (self.__method == RequestMethod.Post or self.__method == RequestMethod.Put or self.__method == RequestMethod.Patch):
            self.__headers = {
                "Content-Type": "application/json"
            }
        self.__timeout = aiohttp.ClientTimeout(timeout)

    def header(self, *args):
        idx, length = 0, len(args)
        if length % 2:
            raise ValueError('Parameters must be a key, value sequence like header(key1, balue1, key2, value2, ...).')
        if not self.__headers or not isinstance(self.__headers, dict):
            self.__headers = dict()

        while idx < length:
            self.__headers[args[idx]] = args[idx + 1]

        return self

    def payload(self, *args):
        idx, length = 0, len(args)
        if length % 2:
            raise ValueError('Parameters must be a key, value sequence like header(key1, balue1, key2, value2, ...).')
        if not self.__payload or not isinstance(self.__payload, dict):
            self.__payload = dict()

        while idx < length:
            self.__payload[args[idx]] = args[idx + 1]

        return self

    async def get(self):
        async with aiohttp.ClientSession(trust_env=True, timeout=self.__timeout) as session:
            async with session.get(self.__url) as response:
                r = await Response(response).read()
                return r
                

    async def post(self):
        async with aiohttp.ClientSession(trust_env=True, timeout=self.__timeout) as session:
            async with session.post(self.__url, json=self.__payload, headers=self.__headers) as response:
                r = await Response(response).read()
                return r

    async def do(self):
        match self.__method:
            case RequestMethod.Get:
                return await self.get()
            case RequestMethod.Post:
                return await self.post()
        # TODO: write other cases
        return None
