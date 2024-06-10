# Backup api.cache
    * In one of below conditions:
        1. When the api.cache folder is reached upon specific size
        2. On a weekly/monthly/whatever-ly interval
      The bot must compress the api.cache folder as .zip, then send the file to bot superusers.
      Then remove the archive folder to prevent the host from being out of space.

# Plus bot group style
    * Consider a standby b ot inside a group; When a member types a message containing Currency/Crypto/Gold names,
    The bot automatically converts that token to equivalents (AutoCalculator). This list of token from which this input must convert to is selected by the,
    vip user that added the bot to group.
    * Note: The names are general: Ot can be persian or english name, or symbol. The language of which the bot sends message is selected by owner too.

# APIs:
    * Ive had implemented async requesting methods. Change whole project GET and POST requests to use this async veriosn.


* There are som duplicates in crypto list file.
