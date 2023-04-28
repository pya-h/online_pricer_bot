Crypto Price Bot
# Language: Python 
This telegram bot is for obtaining last updates on cryptocurrncies.
it also can work as an channel admin to post updates every five minutes.

Requirements (.env file):
x CMC_API-KEY: API KEY obtained from CoinMarketCap API section.
x CHANNEL_ID: The id of the channel you want to add this bot as an admin to. 
x pip install -r requirements.txt

Notice env_format.txt file and create a .env file like it, with your own CMC_API_KEY and CHANNEL_ID though!

# Bot Commands:
/start Start updating the channel, via posting prices every 5 minutes!
/get get current prices as a response inside the bot
/gecko change the source of cryptocurrency prices to CoinGecko
/marketcap change the source of cryptocurrency prices to CoinMarketCap
/stop stop the channel update queue
