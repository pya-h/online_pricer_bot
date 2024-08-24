
# BUGS
- Write a compare script about which coin prices aren't received from ccm
- Fix Empty Tags in Equalizing

# TODO
- Check all LOG categories and re-arrange them.

# Backup api.cache
    * In one of below conditions:
        1. When the api.cache folder is reached upon specific size
        2. On a weekly/monthly/whatever-ly interval
      The bot must compress the api.cache folder as .zip, then send the file to bot superusers.
      Then remove the archive folder to prevent the host from being out of space.