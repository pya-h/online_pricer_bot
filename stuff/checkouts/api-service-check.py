from api.api_async import Request, Response
import asyncio

async def call():
    request = Request("https://api.navasan.tech/latest?api_key=freebJVQLzYAhbCP7N6qpujh90uaC92l")
    response = await request.get()
    print(response.data)

asyncio.run(call())