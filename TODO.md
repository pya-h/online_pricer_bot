# Important Notes

# Remove negative ids
    * The production sqlite database, has a large number of negative IDs inside, because of those who try to run bot in groups.
        while migrating to new bot, remove all these rows.

    * Staging app, is still creating negative ID accounts, for now it's managed by a small filter, 
        But you should find the root of the problem.