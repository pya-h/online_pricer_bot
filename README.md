# Crypto Price Bot
# Language: Python
    This telegram bot is for obtaining last updates on cryptocurrncies.
    it also can work as an channel admin to post updates every five minutes.

Requirements (.env file):
    x CMC_API-KEY: API KEY obtained from CoinMarketCap API section.
    x CHANNEL_ID: The id of the channel you want to add this bot as an admin to.
    x pip install -r requirements.txt

    Read env_format.txt file and create a .env file like it, with your own CMC_API_KEY and CHANNEL_ID though!

# Common Bot Commands:
    /start : Start the bot
    /get get : current prices as a response inside the bot
    /selectcoins : select your desired coins that you want to keep track of their prices.
        once you selected your desired coins, any message you'll get by /get command will just show the price of your desired coins.
        Note that the channel message containing the price list will not be affected by your desired list.
    /gop user password : tries to login you as admin by the username and password you provied in the command arguments
    /leave : leave the bot. will free the bot memory of the customizations you made so far.
# Bot Commands needing admin privillages
    /schedule time_interval : start scheduling the channel update by the interval you've sent in the argument. if interval isnt provided,
        the default interval will be used (5 minutes.)
    /gecko change the source of cryptocurrency prices to CoinGecko
    /marketcap change the source of cryptocurrency prices to CoinMarketCap
    /stop stop the channel update queue

# Note:
    Admin commands need authorization. but you can provide the admin credentials alongside these commands,
        so you won't need to /god before them. like:
    /schedule username password interval
    /gecko username password
    ...
    once you did one admin command as above, the further authorization for other admin commands, won't be needed.
