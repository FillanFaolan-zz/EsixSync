import os
import json
import time

from EsixManager.Exceptions import LoadConfigException, SummaryFileMissingException
from EsixManager.Model import EsixConfig
from EsixManager.Model.RepoSummary import RepoSummary
from EsixManager.Constants import REPO_SUMMARY_FILE_PATH, CONFIG_FILE_PATH


def LoadFile(path: str) -> str:
    if not os.path.isfile(path):
        return None
    else:
        f = open(path, 'r')
        content = "".join(f.readlines())
        return None if content == "" else content


def StoreFile(path: str, content: str) -> None:
    folder, filename = os.path.split(path)
    if not os.path.exists(folder):
        os.makedirs(folder)
    f = open(path, 'w')
    f.write(content)


def LoadSummary(repoFolder: str) -> RepoSummary:
    summaryFilePath = repoFolder + REPO_SUMMARY_FILE_PATH
    data = LoadFile(summaryFilePath)
    if data is not None:
        dictData = json.loads(data)
        summary = RepoSummary()
        summary.__dict__ = dictData
        return summary
    else:
        raise SummaryFileMissingException(summaryFilePath)


# store summary will handle time
def StoreSummary(repoFolder: str, summary: RepoSummary) -> None:
    path = repoFolder + REPO_SUMMARY_FILE_PATH
    # set updated_at var
    summary.updatedAt = time.time()
    data = json.dumps(dict(summary))
    StoreFile(path, data)


def LoadConfig() -> EsixConfig:
    path: str = CONFIG_FILE_PATH
    try:
        config: EsixConfig = EsixConfig()
        jsonConfig = LoadFile(path)
        # if the config exists, load it
        if jsonConfig is not None:
            result = json.loads(jsonConfig)
            config.__dict__ = result
        else:
            config = EsixConfig.GetDefaultConfig()
            StoreConfig(config)
        return config
    except:
        raise LoadConfigException(path)


def StoreConfig(config: EsixConfig) -> None:
    path = CONFIG_FILE_PATH
    StoreFile(path, json.dumps(dict(config)))
