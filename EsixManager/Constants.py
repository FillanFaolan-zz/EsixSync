import os
import sys

from EsixManager.Interface.BuiltinDownloader import BuiltinDownloader

STORE_POSTS_INFO = True
POSTS_INFO_FOLDER = "/.info"
REPO_SUMMARY_FILE_PATH = "/.summary.json"
CONFIG_FILE_PATH = os.environ['HOME'] + "/.e6sync.conf.json"
BUILTIN_DOWNLOADER = BuiltinDownloader()
