import _thread
import os
import sys
import threading
import time
import requests
import json
from queue import Queue
from CommandLine.Addon.ProgressBar import ProgressBar
from EsixManager.Interface.IDownloader import IDownloader
from EsixManager.Utilities import LoadFile, StoreFile


class DownloadTask(threading.Thread):
    indexer = None
    url = None
    fileName = None
    storeFolder = None
    cookies = None
    OnCompleteCallback = None
    headers = {
        # Follow the instruction from e621, use a custom user-agent
        "User-Agent": "EsixSyncDownloader/1.0"
    }
    _complete = False
    _calculateSpeed = True
    # False : Don't stop, True : stop
    _stopSignal = False
    _fileSize = 0
    _progressUpdateInterval = 1.0  # 1 second
    _bufferSize = 4096  # Bytes
    _downloadedBytes = 0
    _downloadingSpeed = 0
    _tmpFileSuffix = ".tmp"
    # last calculate time
    _lastSpeedCalcTime = 0.0
    _lastSpeedCalcDownloaded = 0

    def _CalculateSpeed(self):
        while not self._complete:
            nowTime = time.time()
            nowBytes = self._downloadedBytes
            timeGap = nowTime - self._lastSpeedCalcTime
            self._lastSpeedCalcTime = nowTime
            bytesGap = nowBytes - self._lastSpeedCalcDownloaded
            self._lastSpeedCalcDownloaded = nowBytes
            self._downloadingSpeed = bytesGap / timeGap
            # update speed evey 200 ms
            time.sleep(0.2)

    def GetProgress(self):
        downloaded = self.GetDownloadedBytes()
        if self._fileSize < 1:
            return 0
        return downloaded / self._fileSize

    def GetSpeed(self):
        return self._downloadingSpeed

    def GetDownloadedBytes(self):
        return self._downloadedBytes

    def GetFileSize(self):
        return self._fileSize

    def Begin(self):
        # self._stopSignalLock.acquire()
        self._stopSignal = False
        self._complete = False
        # self._stopSignalLock.release()
        self.start()
        if self._calculateSpeed:
            _thread.start_new_thread(self._CalculateSpeed, ())
        # if use self.run(), this function will work in sync mode

    def Stop(self):
        self._stopSignal = True

    def run(self) -> None:
        absoluteTempFilePath = self.storeFolder + "/" + self.fileName + self._tmpFileSuffix
        absoluteFilePath = self.storeFolder + "/" + self.fileName
        # create path if not exists
        if not os.path.exists(self.storeFolder):
            os.makedirs(self.storeFolder)
        # use get method to download
        resp = requests.get(url=self.url, stream=True, headers=self.headers, cookies=self.cookies)
        totalBytes = int(resp.headers["Content-Length"])
        self._fileSize = totalBytes
        currentBytes = 0
        # write to file
        with open(absoluteTempFilePath, "wb") as tempFile:
            for chunk in resp.iter_content(chunk_size=self._bufferSize):
                if chunk:
                    tempFile.write(chunk)
                    currentBytes += len(chunk)
                    self._downloadedBytes = currentBytes
                    if self._stopSignal:
                        return
                    # self._stopSignalLock.release()
        os.rename(absoluteTempFilePath, absoluteFilePath)
        self._complete = True
        if self.OnCompleteCallback is not None:
            self.OnCompleteCallback(self.indexer)


class AsyncDownloader(IDownloader):
    _downloadQueue = Queue()
    # item = {url:"url", path:"path", cookie= { ... }}
    _downloadList = []
    _downloadedItemCount = 0
    _downloadingTasks = dict()
    _queueLock = threading.Lock()
    # maximum download count at a time
    _maxDownloadItemCount = 3
    _taskSummaryFileName = ".%s.tasks.json" % int(time.time())
    displayUi = True
    taskSummaryFilePath = sys.path[0]

    def __init__(self):
        self.Clear()

    # cleanup this downloader
    def Clear(self):
        self._downloadQueue = Queue()
        self._downloadedItemCount = 0
        self._downloadingTasks = dict()
        self._taskSummaryFileName = ".%s.tasks.json" % int(time.time())
        self.taskSummaryFilePath = sys.path[0]

    def _OnCompleteCallback(self, downloadIndexer: int):
        self._queueLock.acquire()
        self._downloadingTasks.pop(downloadIndexer)
        self._downloadList = self._downloadList[1:]
        self._downloadedItemCount += 1
        self.StoreTasks()
        self._queueLock.release()

    # auto convert B/s to KB/s MB/s or GB/s
    # (won't to TB/s because I assume the internet speed won't reach that quick in 5 years OwO
    def _BytesPerSecondsToStr(self, bytesPerSecond: float):
        suffixes = ["B/s", "KB/s", "MB/s", "GB/s"]
        space = ' '
        suffixPointer = 0
        while bytesPerSecond / 1024 >= 1 and suffixPointer < len(suffixes) - 1:
            bytesPerSecond /= 1024
            suffixPointer += 1
        return "%.2f" % bytesPerSecond + space + suffixes[suffixPointer]

    # list must be the same format as _downloadList
    def LoadTasks(self, path: str):
        self.taskSummaryFilePath, self._taskSummaryFileName = os.path.split(path)
        self._downloadList = json.loads(LoadFile(path))
        # add all files to queue
        for item in self._downloadList:
            self._queueLock.acquire()
            task = DownloadTask()
            task.url = item["url"]
            task.storeFolder, task.fileName = os.path.split(item["path"])
            cookies = item["cookies"]
            # task.cookies = cookies
            self._downloadQueue.put(task)
            self._queueLock.release()

    def StoreTasks(self):
        jsonTasks = json.dumps(self._downloadList)
        StoreFile(self.taskSummaryFilePath + '/' + self._taskSummaryFileName, jsonTasks)

    def FetchAllItems(self):
        index = 0
        # qsize is the MAX INDEX OF THE QUEUE
        progressBar = ProgressBar(minValue=0, maxValue=self._downloadQueue.qsize() + 1)
        # while there are still task waiting to download or there are still active tasks
        while (self._downloadQueue.qsize() > 0) or (len(self._downloadingTasks) > 0):
            # trying to emit a task if lock is acquired and queue is not empty
            while len(self._downloadingTasks) < self._maxDownloadItemCount and self._downloadQueue.qsize() > 0:
                # there are still somewhere for a new task, emit one, lock will wait for 200 ms
                if self._queueLock.acquire(timeout=0.2):
                    task = self._downloadQueue.get()
                    task.indexer = index
                    self._downloadingTasks[index] = task
                    task.OnCompleteCallback = self._OnCompleteCallback
                    # index is a artifact key for the tasks, with index we can remove item from downloadingTasks
                    index += 1
                    task.Begin()
                    self._queueLock.release()
            # build output
            if self.displayUi:
                progressBarExt = ", Speed : {speed} "
                downloadedItemCount = self._downloadedItemCount
                progressBar.curValue = downloadedItemCount
                # compute speed
                bytesPerSecond = 0
                itemCount = 0
                for i in self._downloadingTasks.keys():
                    bytesPerSecond += self._downloadingTasks[i].GetSpeed()
                    itemCount += 1
                bytesPerSecond = bytesPerSecond / itemCount
                progressBar.extContent = progressBarExt.format(speed=self._BytesPerSecondsToStr(bytesPerSecond))
                print("\r" + progressBar.GetProgressBarString(), end="")
            # sleep for 500 ms
            time.sleep(0.5)
        # just for a new line
        if self.displayUi:
            # print a complete progressbar to display 100% complete
            progressBar.extContent = ", Done "
            # make sure it shows 100%
            progressBar.curValue = progressBar.maxValue
            print("\r" + progressBar.GetProgressBarString(), end="")
            print("")
        sumPath = self.taskSummaryFilePath + '/' + self._taskSummaryFileName
        # remove task cache
        if os.path.isfile(sumPath):
            os.remove(sumPath)

    # in this case, this function will not start download immediately but to storage task into _downloadQueue
    def Download(self, url: str, path: str, loginId: str = None, apiToken: str = None) -> None:
        cookies = None
        # in case download needs cookie
        if loginId == "" or apiToken == "" or loginId is None or apiToken is None:
            cookies = {"login": loginId, "api_key": apiToken}
        task = DownloadTask()
        task.url = url
        task.storeFolder, task.fileName = os.path.split(path)
        # task.cookies = cookies
        dictTasks = {"url": url, "path": path, "cookies": cookies}
        # push this task into main queue
        self._downloadQueue.put(task)
        self._downloadList = self._downloadList + [dictTasks]
        self.StoreTasks()
