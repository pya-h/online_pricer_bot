from enum import Enum
import aiohttp
from typing import Dict
from json import loads as json_parse

class RequestMethod(Enum):
    Get = 1
    Post = 2
    Put = 3
    Patch = 4
    Delete = 5


class Response:
    def __init__(self, response: aiohttp.ClientResponse) -> None:
        self.response: aiohttp.ClientResponse = response
        self.__raw: str = None
        self.__decoded: Dict[str, any] | str = self.__raw

    async def read(self):
        self.__raw = await self.response.text()

        if self.response.content_type == 'application/json':
            self.__decoded = await self.response.json()
            
        try:
            self.__decoded = json_parse(self.__raw)
        except:
            pass
            
        return self
    
    @property
    def status(self) -> int:
        return self.response.status

    @property
    def OK(self) -> bool:
        return self.status == 200 or self.status == 201  # TODO: What about 202 to 300
    
    @property
    def data(self):
        '''Decoded[if json] result of request.'''
        return self.__decoded

    @property
    def text(self):
        '''The exact string returned from request.'''
        return self.__raw
    
    

class Request:

    def __init__(self, url: str, payload: dict = None, headers: dict=None, method: RequestMethod=RequestMethod.Get, timeout: float = 5.0) -> None:
        self.__url = url
        self.__payload = payload
        self.__method = method
        self.__headers = headers
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

        while idx < length - 1:
            self.__headers[args[idx]] = args[idx + 1]
            idx += 1
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
        async with aiohttp.ClientSession(trust_env=True, headers=self.__headers, timeout=self.__timeout) as session:
            async with session.get(self.__url) as response:
                r = await Response(response).read()
                return r
                

    async def post(self):
        async with aiohttp.ClientSession(trust_env=True, headers=self.__headers, timeout=self.__timeout) as session:
            async with session.post(self.__url, json=self.__payload) as response:
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
