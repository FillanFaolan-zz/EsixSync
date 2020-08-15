class EsixConfig:
    # the folder list which will sync with e621, which key is be a unique repo name, value is the folder path
    repositoryPair = {}
    # filename template, you can use {image_index} {image_md5} {author} {width} {height} {rating} {image_ext} {post_id}
    # you must use at least one variant from {image_index} or {post_id} to avoid collide on filename
    filenameTemplate = None
    # [OPTIONAL] the login id of the e621
    loginId = None
    # [OPTIONAL] the api token of the e621
    apiToken = None

    def keys(self):
        return ("repositoryPair", "filenameTemplate", "loginId", "apiToken")

    def __getitem__(self, item):
        return getattr(self, item)

    # return the default config
    @staticmethod
    def GetDefaultConfig():
        default = EsixConfig()
        default.repositoryPair = {}
        default.filenameTemplate = "{author}_{image_index}.{image_ext}"
        default.loginId = ""
        default.apiToken = ""
        return default
