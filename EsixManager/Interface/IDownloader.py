from abc import ABCMeta as AbstractClassMeta
from abc import abstractmethod


class IDownloader(metaclass=AbstractClassMeta):
    @abstractmethod
    def Download(self, url: str, path: str, loginId: str, apiToken: str) -> None:
        pass
