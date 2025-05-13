from api.tether_service import NobitexService
from decouple import config
import api.api_async as api

token = config("NOBITEX_TOKEN")
nb = NobitexService(token)


async def get():
    res = await nb.get()
    print(nb.recent_response)
    print(res)


if __name__ == "__main__":
    api.run_async(get)
