# Important Notes

# Remove negative ids
    * The production sqlite database, has a large number of negative IDs inside, because of those who try to run bot in groups.
        while migrating to new bot, remove all these rows.

    * Staging app, is still creating negative ID accounts, for now it's managed by a small filter, 
        But you should find the root of the problem.


    * Language Update:
        * There must be a state for persian language that will use english symbols with persian text.
         You could use 'FA', 'fa' and 'en' for languages; this way 'FA' and 'fa' will have same value with .lower() method
         and different values when needed.

    * Enhance logging system -> Define a new Log class and LogType Enum and some other enhancements.