# Important Notes

# Remove negative ids
    * The production sqlite database, has a large number of negative IDs inside, because of those who try to run bot in groups.
        while migrating to new bot, remove all these rows.

    * Enhance logging system -> Define a new Log class and LogType Enum and some other enhancements.

    * After finishing this stage, Remove and throw away any function, class or whatever if its not needed,
        after backing them up in a separate branch 