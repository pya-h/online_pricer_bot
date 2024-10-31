# Crypto Price Bot
# Language: Python
This telegram bot is for obtaining last updates on cryptocurrncies.
it also can work as an channel admin to post updates every five minutes.

# Requirements (.env file):
* BOT API TOKEN: The token you got from the botfather
* CMC_API-KEY: API KEY obtained from CoinMarketCap API section. (Free/VIP modes: CoinMarketCap.com)
* CURRENCY_TOKEN: API KEY obtained from SourceArena. (You have to upgrade your account to VIP in sourcearena.ir)
* ABAN_TETHER_TOKEN: This api key is used just for obtaining Tether price in tomans. (Free: abantether.com)
* CHANNEL_ID: The id of the channel you want to add this bot as updater to it. you must give channel admin previllages to the bot.
    Only users that subscribe this channel (and channel related to SECOND_CHANNEL_ID, if set) can use bot features.
* ADMIN_USERNAME | ADMIN_PASWORD: desired admin credentials.
* SECOND_CHANNEL_ID: if you set this, Only users that subscribe this bot (and channel related to CHANNEL_ID obviously!), can use bot features.
* pip install -r requirements.txt

# Common Bot Commands:
* /start : Start the bot
* /get: get current prices as a response inside the bot
* /crypto : select your desired coins that you want to keep track of their prices.
    once you selected your desired coins, any message you'll get by
    /get command will just show the price of your desired coins.
    Note that the channel message containing the price list
    will not be affected by your desired list.
* /currency : select your desired currencies(Physical Money units, oil, gold, etc) that you want to keep track of their prices.
    once you selected your desired currencies, any message you'll get by
    /get command will just show the price of your desired currencies.
    Note that the channel message containing the price list
    will not be affected by your desired list.
* /currency : select your desired golds that you want to keep track of their prices.
    once you selected your desired currencies, any message you'll get by
    /get command will just show the price of your desired golds.
    Note that the channel message containing the price list
    will not be affected by your desired list.
* /god user password : tries to login you as admin by the username
     and password you provied in the command arguments

# Bot Commands needing admin privillages
* /schedule time_interval : start scheduling the channel update
    by the interval you've sent in the argument.
    if interval isnt provided, the default interval will be used (5 minutes.)
* /gecko change the source of cryptocurrency prices to CoinGecko
* /marketcap change the source of cryptocurrency prices to CoinMarketCap
* /stop stop the channel update queue
* /post : enables to send a post to all active users; just click the command, write a text message(voice/audio/photo/etc are supported too)
    and send. Bot will start sending the post while showing you the progress as in percentage.
* /stats: Shows a brief report of bot users; report consists of the number of users that have been active within: today/yesterday/last week/last year
    and number of all users in total.

# Admin Keyboard
once you authenticated yourself as admin you will see 4 new options in keyboard below the bot.
* Statistics: Shortcut for /stats command
* Notify: Shortcut for /post command
* Start Channel Scheduling: Shortcut for /schedule command
* Stop Schedule: Shortcut for /stop command
  
# Note:
* User who is authenticated as Admin, will be logged out after 30 minutes of inactivity; just for security purposes. and alongside that the admin keyboard will be hidden again.
* For enhancing performance, active users data will be cached in memory; Also there is a GarbageCollector method running every hour to free memory from inactive users.
* For now Using CoinGecko as source, may encounter some bugs that will be fixed soon.
* Admin commands need authorization. but you can provide the admin credentials
    alongside these commands, so you won't need to /god before them. like:
/schedule username password interval
/gecko username password
   .
    once you did one admin command as above, the further authorization
        for other admin commands, won't be needed.
