import os
import requests
from EsixManager.Interface.IDownloader import IDownloader


class DownloadTask():
    url = None
    fileName = None
    storeFolder = None
    cookies = None
    headers = {
        "User-Agent": "EsixSyncDownloader/1.0"
    }
    _fileSize = 0
    _bufferSize = 4096
    _tmpFileSuffix = ".tmp"

    def Fetch(self) -> None:
        absoluteTempFilePath = self.storeFolder + "/" + self.fileName + self._tmpFileSuffix
        absoluteFilePath = self.storeFolder + "/" + self.fileName
        # create path if not exists
        if not os.path.exists(self.storeFolder):
            os.makedirs(self.storeFolder)
        # use get method to download
        resp = requests.get(url=self.url, stream=True, headers=self.headers, cookies=self.cookies)
        total = int(resp.headers["Content-Length"])
        self._fileSize = total
        current = 0
        # write to file
        with open(absoluteTempFilePath, "wb") as tempFile:
            for chunk in resp.iter_content(chunk_size=self._bufferSize):
                if chunk:
                    tempFile.write(chunk)
                    current += len(chunk)

        os.rename(absoluteTempFilePath, absoluteFilePath)


class BuiltinDownloader(IDownloader):

    def Download(self, url: str, path: str, loginId: str = None, apiToken: str = None) -> None:
        # cookies = None
        # in case download needs cookie
        # if loginId == "" or apiToken == "" or loginId is None or apiToken is None:
        #    cookies = {"login": loginId, "api_key": apiToken}
        task = DownloadTask()
        task.url = url
        task.storeFolder, task.fileName = os.path.split(path)
        # task.cookies = cookies
        task.Fetch()
