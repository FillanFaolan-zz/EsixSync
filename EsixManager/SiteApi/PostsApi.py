from EsixManager.SiteApi.Base import ApiBase


class PostsApi(ApiBase):
    """
        def _GetMaxPageCount(self, tags):
        regexPattern = '''(?<=\\>)[0-9]{1,}(?=\\<)'''
        htmlResp = self.Get("/posts?tags={tags}".format(tags=tags)).text
        print(htmlResp)
        regex.match(pattern=regexPattern, string=htmlResp)
    """

    # function will use search from page 1 to 1 + maxPageQueryDepth, and when md5 collide happening, stop
    def ListPosts(self, tags: str, page: int = 1):
        # stop program from stress the e621 server
        jsonResp = self.Get("/posts.json",
                            paramDict={"page": page, "tags": tags, "limit": self.picPerPage}
                            ).json()
        if jsonResp.__contains__("posts"):
            return jsonResp["posts"]
        else:
            return []
