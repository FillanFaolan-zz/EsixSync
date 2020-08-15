from EsixManager.SiteApi.Base import ApiBase


class PoolApi(ApiBase):
    def Search(self, **params):
        """
        search[name_matches] Search pool names.
        search[id] Search for a pool ID, you can search for multiple IDs at once, separated by commas.
        search[description_matches] Search pool descriptions.
        search[creator_name] Search for pools based on creator name.
        search[creator_id] Search for pools based on creator ID.
        search[is_active] If the pool is active or hidden. (True/False)
        search[is_deleted] If the pool is deleted. (True/False)
        search[category] Can either be “series” or “collection”.
        search[order] The order that pools should be returned, can be any of: name, created_at, updated_at, post_count. If not specified it orders by updated_at
        limit The limit of how many posts should be retrieved.
        """
        modifiedParams = dict()
        for key in params.keys():
            if params[key] == "limit":
                modifiedParams[key] = params[key]
            else:
                modifiedParams["search[%s]" % key] = params[key]
        resp = self.Get("/pools.json", modifiedParams)
        return resp.json()

    # Use the e621 Posts and Pools API, cuz use only Pools API will preform A LOT MORE HEAVY STRESS to the server
    def ListPosts(self, poolId, page: int = 1):
        # stop program from stress the e621 server, decided not to use pool api cuz it will lead several api call
        # after query all posts id in the pool in order to query the posts download url
        jsonResp = self.Get(
            "/posts.json",
            paramDict={"page": page, "tags": "pool:%s" % poolId, "limit": self.picPerPage}
        ).json()
        if jsonResp.__contains__("posts"):
            return jsonResp["posts"]
        else:
            return []
