## Priorities
    * Automatically Identify & Connect Channels (Just like groups); [In addition to old approaches]

    * Admin option to switch USD/USDT price sources
        USD: Navasan, SourceArena, FromUSDT
        USDT: Nobitex, AbanTether, Navasan

    * Enhance logging system -> Define a new Log class and LogType Enum and some other enhancements.
        maybe use an external module?

    * Maybe cache prices, so when the server restarts, it has previous prices.

    * Admin Option to Add/Remove tokens to/from Each List
        - Also remember removing a token from all users list, if admin decides to remove a token.

    * Add switch to disable Receiving admin notification (for special users maybe, or maybe a hidden feature)


## Side notes
    * Voting & Polling platform, e.g. for adding a new token: users participate in a poll with a list of new tokens; 
        the popular one will be automatically added to token list.
        - Also needs extra panel for admin to create the poll. Dependency: Add/Remove tokens feature
    

    * Maybe complete CoinGeckoService class?