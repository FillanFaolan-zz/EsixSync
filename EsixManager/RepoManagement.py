import json
import os
from math import ceil, floor
# import custom parts
from EsixManager.Exceptions import PoolNotExistsException, RepoNotExistsException, RepoDuplicatedException
from EsixManager.SiteApi.PoolApi import PoolApi
from EsixManager.SiteApi.PostsApi import PostsApi
from EsixManager.Model.RepoSummary import RepoSummary
# import utilities
from EsixManager.Utilities import LoadConfig
from EsixManager.Utilities import StoreConfig
from EsixManager.Utilities import StoreFile
from EsixManager.Utilities import LoadSummary
from EsixManager.Utilities import StoreSummary
# import downloader interface
from EsixManager.Interface.IDownloader import IDownloader
# import constants
from EsixManager.Constants import POSTS_INFO_FOLDER
from EsixManager.Constants import REPO_SUMMARY_FILE_PATH
from EsixManager.Constants import BUILTIN_DOWNLOADER
from EsixManager.Constants import STORE_POSTS_INFO


# functions for locally operate repo files
# get repo folder from repo name
def GetRepoFolderPath(repoName: str):
    repoPair = LoadConfig().repositoryPair
    if repoName in repoPair.keys():
        return repoPair[repoName]
    else:
        raise RepoNotExistsException(repoName)


# init a folder for sync
def InitRepo(repoName: str, repoFolder: str, folderType: str, identifier: str) -> None:
    config = LoadConfig()
    summary = RepoSummary()
    summary.repoType = folderType
    summary.repoIdentifier = identifier
    summaryPath = repoFolder + REPO_SUMMARY_FILE_PATH
    # repo name or repo folder must be unique
    if (repoName in config.repositoryPair.keys()) or (repoFolder in config.repositoryPair.values()):
        raise RepoDuplicatedException(repoName, repoFolder)
    # make dir if this dir is not exists
    if not (os.path.exists(repoFolder) and os.path.isdir(repoFolder)):
        os.makedirs(repoFolder)
    # make summary.json if it is not exists
    if not (os.path.exists(summaryPath) and os.path.isfile(summaryPath)):
        StoreFile(summaryPath, json.dumps(dict(summary)))
    else:
        raise RepoDuplicatedException(repoName, repoFolder)
    config.repositoryPair[repoName] = repoFolder
    StoreConfig(config)


def RebuildSummary(repoName: str, folderType: str, identifier: str):
    # postsExt = ["jpg", "png", "bmp", "gif", "webm", "mp4"]
    config = LoadConfig()
    pairs = config.repositoryPair
    if repoName not in pairs.keys():
        raise RepoNotExistsException(repoName)
    else:
        repoFolder = pairs[repoName]
    summary = RepoSummary()
    summary.repoType = folderType
    summary.repoIdentifier = identifier
    summaryPath = repoFolder + REPO_SUMMARY_FILE_PATH
    # make dir if this dir is not exists
    if not (os.path.exists(repoFolder) and os.path.isdir(repoFolder)):
        os.makedirs(repoFolder)
    # rebuild summary.json
    StoreFile(summaryPath, json.dumps(dict(summary)))


# remove folder from sync paths
def RemoveRepo(repoName: str) -> None:
    config = LoadConfig()
    try:
        config.repositoryPair.pop(repoName)
        StoreConfig(config)
    except KeyError:
        raise RepoNotExistsException(repoName)


# get info including update count, update checking time
def GetRepoSummaries(self) -> list:
    foldersInfo = []
    repos = self._config.repositoryPair
    for repoName in repos.keys():
        folder = repos[repoName]
        summary = LoadSummary(folder)
        foldersInfo += [summary]
    return foldersInfo


# get folder's summary
def GetRepoSummary(repoName: str) -> RepoSummary:
    folder = GetRepoFolderPath(repoName)
    return LoadSummary(folder)


# allow or denied folder to update
def SetRepoPinned(repoName: str, canUpdate: bool) -> None:
    config = LoadConfig()
    repoFolder = GetRepoFolderPath(repoName)
    folders = config.repositoryPair
    if folders.__contains__(repoName):
        summary = LoadSummary(repoFolder)
        summary.pinned = canUpdate
        StoreSummary(repoFolder, summary)
    else:
        raise RepoNotExistsException(repoName)


# set a folder's alias
def SetRepoName(repoName: str, newName: str) -> None:
    config = LoadConfig()
    repoFolder = GetRepoFolderPath(repoName)
    if config.repositoryPair.__contains__(repoName):
        config.repositoryPair.pop(repoName)
        config.repositoryPair[newName] = repoFolder
        StoreConfig(config)
    else:
        raise RepoNotExistsException(repoName)


# class for update
class RepoUpdateManager:
    _config = None
    _poolApi = None
    _postsApi = None
    _downloader = None

    # _statReporter = None

    def __init__(self, downloader: IDownloader = BUILTIN_DOWNLOADER):
        self._poolApi = PoolApi()
        self._postsApi = PostsApi()
        self._LoadConfig()
        self._downloader = downloader
        # self._statReporter = statReporter

    # set login and api_key field
    def _SetLoginParams(self, login: str = None, apiToken: str = None) -> None:
        if login is None or apiToken is None or login == "" or apiToken == "":
            return
        else:
            loginParams = {"login": login, "api_key": apiToken}
            self._poolApi.loginParams = loginParams
            self._postsApi.loginParams = loginParams

    # load config from $HOME/.hexesix.conf.json
    def _LoadConfig(self) -> None:
        self._config = LoadConfig()
        # set login params
        self._SetLoginParams(self._config.loginId, self._config.apiToken)

    # store config from $HOME/.hexesix.conf.json
    def _StoreConfig(self) -> None:
        StoreConfig(self._config)

    # update .summary file in a folder
    def _UpdateRepoSummaryFile(self, repoName: str) -> RepoSummary:
        repoFolder = self._GetRepoFolderPath(repoName)
        summary = LoadSummary(repoFolder)
        result = None
        # there is no "do not update" flag or "do not update" flag is set to false
        if summary.pinned is not True:
            if summary.repoType == "pool":
                result = self._UpdatePoolRepoSummaryFile(repoFolder, summary)
            elif summary.repoType == "posts":
                result = self._UpdatePostsRepoSummaryFile(repoFolder, summary)
            StoreSummary(repoFolder, result)
        else:
            result = summary
        return result

    # update .summary for a pool sync folder
    def _UpdatePoolRepoSummaryFile(self, repoFolder: str, summary: RepoSummary) -> RepoSummary:
        self._LoadConfig()
        api = self._poolApi
        pid = int(summary.repoIdentifier)
        poolInfo = self._poolApi.Search(id=pid)
        if len(poolInfo) < 1:
            raise PoolNotExistsException(pid)
        else:
            poolInfo = poolInfo[0]
            poolId = poolInfo["id"]
            # if there is any update, it will be different in the field of 'post_count' will be bigger than len(md5)
            if len(summary.fileMetadata) < poolInfo["post_count"]:
                maxPage = ceil(poolInfo["post_count"] / self._poolApi.picPerPage)
                allPosts = []
                # walk all the way to page 1, until the md5 is collided
                for page in range(maxPage, 0, -1):
                    stopWalking = False
                    newPosts = []
                    posts = api.ListPosts(poolId, page)
                    for post in posts:
                        # avoid posts in download queue or downloaded
                        if post["file"]["md5"] in [info["md5"] for info in summary.fileMetadata.values()] or \
                                post["file"]["md5"] in [info["md5"] for info in summary.downloadQueue.values()]:
                            stopWalking = True
                            continue
                        else:
                            newPosts += [post]
                    allPosts = newPosts + allPosts
                    if stopWalking:
                        break
                # reverse allPosts to make it in right order
                allPosts.reverse()
                # write summary.queue
                index = len(summary.fileMetadata) + 1
                for post in allPosts:
                    postFileName = self._config.filenameTemplate.format(
                        image_index=index,
                        image_md5=post["file"]["md5"],
                        author="-".join(post["tags"]["artist"]),
                        width=post["file"]["width"],
                        height=post["file"]["height"],
                        rating=post["rating"],
                        image_ext=post["file"]["ext"],
                        post_id=post["id"]
                    )
                    summary.downloadQueue[postFileName] = {
                        "url": post["file"]["url"],
                        "md5": post["file"]["md5"],
                        "id": post["id"]
                    }
                    # summary.fileMd5Pair[postFileName] = post["file"]["md5"]
                    # summary.postsIdPair[postFileName] = post["id"]
                    index += 1
                # if store image info
                if STORE_POSTS_INFO and allPosts is not None:
                    self._StorePostsInfoFiles(repoFolder, allPosts)
            return summary

    # update .summary for a posts sync folder
    def _UpdatePostsRepoSummaryFile(self, repoFolder: str, summary: RepoSummary) -> RepoSummary:
        self._LoadConfig()
        api = self._postsApi
        # cannot use ceil, len(md5) can be 0
        currentPage = floor(len(summary.fileMetadata) / api.picPerPage) + 1
        allPosts = []
        # if there is any update, it will be different in the field of 'post_count' will be bigger than len(md5)
        while True:
            pagePosts = api.ListPosts(tags=summary.repoIdentifier, page=currentPage)
            for post in pagePosts:
                # avoid posts in download queue or downloaded
                if post["file"]["md5"] in [info["md5"] for info in summary.fileMetadata.values()] or \
                        post["file"]["md5"] in [info["md5"] for info in summary.downloadQueue.values()]:
                    continue
                else:
                    allPosts = allPosts + [post]
            if len(pagePosts) != api.picPerPage:
                break
            currentPage += 1
        # reverse allPosts to make it in right order
        allPosts.reverse()
        # write summary.queue
        index = len(summary.fileMetadata) + 1
        for post in allPosts:
            postFileName = self._config.filenameTemplate.format(
                image_index=index,
                image_md5=post["file"]["md5"],
                author="-".join(post["tags"]["artist"]),
                width=post["file"]["width"],
                height=post["file"]["height"],
                rating=post["rating"],
                image_ext=post["file"]["ext"],
                post_id=post["id"]
            )
            summary.downloadQueue[postFileName] = {
                "url": post["file"]["url"],
                "md5": post["file"]["md5"],
                "id": post["id"]
            }
            # summary.fileMd5Pair[postFileName] = post["file"]["md5"]
            # summary.postsIdPair[postFileName] = post["id"]
            index += 1
        # if store image info
        if STORE_POSTS_INFO and allPosts is not None:
            self._StorePostsInfoFiles(repoFolder, allPosts)
        return summary

    # store posts info to ./POST_INFO_PATH, pool will use the same operation
    @staticmethod
    def _StorePostsInfoFiles(repoFolder: str, posts: list) -> None:
        # subFolder = repoFolder + self._config.infoSubFolder
        subFolder = repoFolder + POSTS_INFO_FOLDER
        for post in posts:
            StoreFile(subFolder + "/" + "%s.json" % post["id"], json.dumps(post))

    def _GetRepoFolderPath(self, repoName: str):
        self._LoadConfig()
        repoPair = self._config.repositoryPair
        return repoPair[repoName]

    # update single .summary file with the repo name
    def UpdateRepoSummaryFile(self, repoName: str) -> RepoSummary:
        return self._UpdateRepoSummaryFile(repoName)

    # update all .summary files in configured folders, mainly to update fill queue field
    def UpdateRepoSummaryFiles(self) -> list:
        self._LoadConfig()
        summaryList = []
        for repoName in self._config.repositoryPair.keys():
            # folder = self._config.repositoryPair[repoName]
            summary = self._UpdateRepoSummaryFile(repoName)
            if summary is not None:
                summaryList += [summary]
        # report update complete
        # self._statReporter.ReportAllRepoUpdateComplete()
        return summaryList

    # sync a single repo
    def SyncRepository(self, repoName: str):
        summary = LoadSummary(self._GetRepoFolderPath(repoName))
        repoFolder = self._GetRepoFolderPath(repoName)
        if summary is None:
            raise RepoNotExistsException(repoName)
        if summary.pinned is not False:
            return
        summary.recentlySyncedPosts = list()
        while len(summary.downloadQueue) > 0:
            fileName, fileInfo = summary.downloadQueue.popitem()
            fileUrl, fileMd5, postId = fileInfo["url"], fileInfo["md5"], fileInfo["id"]
            # some file needs you login to view it
            # if you are not yet login, same file still be detected during next update
            if fileUrl is None:
                continue
            self._downloader.Download(
                url=fileUrl,
                path=repoFolder + "/" + fileName,
                loginId=self._config.loginId,
                apiToken=self._config.apiToken
            )
            summary.recentlySyncedPosts += [fileName],
            summary.fileMetadata[fileName] = {"id": postId, "md5": fileMd5}
            StoreSummary(repoFolder, summary)
        # when downloaded
        # self._statReporter.ReportRepoSyncComplete(repoName, self._GetRepoFolderPath(repoName), summary)

    # before sync, you have to UpdateSummaryFiles or it won't sync any new image
    def SyncRepositories(self):
        self._LoadConfig()
        for repoName in self._config.repositoryPair:
            self.SyncRepository(repoName)
        # self._statReporter.ReportAllRepoSyncComplete()
