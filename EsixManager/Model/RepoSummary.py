class RepoSummary:
    # can be "pool" or "posts"
    repoType = ""
    # tags or pool id
    repoIdentifier = ""
    # a dict which key is a filename under the folder, value is the md5 of the file, you can get pic count with this too
    fileMetadata = dict()
    # do not update flag
    pinned = False
    # a dict which key is a filename under the folder, value is the id of the post
    # postsIdPair = dict()
    # a dict of file url for this folder to update, if this dict is empty, then the folder is up-to-date
    downloadQueue = dict()
    # the latest posts compared to last updated, item is the filename
    recentlySyncedPosts = list()
    # the time span of this summary updated, which unit is seconds
    updatedAt = 0.0

    # let this struct can be converted to dict
    def keys(self):
        return (
            "repoType",
            "repoIdentifier",
            "pinned",
            "fileMetadata",
            "downloadQueue",
            "updatedAt",
            "recentlySyncedPosts"
        )

    # let this struct can be converted to dict
    def __getitem__(self, item):
        return getattr(self, item)
