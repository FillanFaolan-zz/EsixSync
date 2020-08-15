import os
import sys
import time
import fire
import prettytable as ptt
from os import path, listdir
from colorama import Fore, Style
from EsixManager.RepoManagement import RepoUpdateManager, RemoveRepo, RebuildSummary
from EsixManager.Exceptions import RepoNotExistsException
from EsixManager.RepoManagement import InitRepo
from EsixManager.SiteApi.PoolApi import PoolApi
from EsixManager.Utilities import LoadConfig, LoadSummary, StoreConfig, LoadFile
from CommandLine.Addon.Downloader import AsyncDownloader

# time format use by the whole program
TIME_FORMAT = "%Y-%m-%d %H:%M:%S %p"
ConvertFloatTime = lambda floatTime: time.strftime(TIME_FORMAT, time.gmtime(floatTime))

# variants for public use
manager: RepoUpdateManager
downloader: AsyncDownloader
commandHelp = {
    "about": "Usage: esync about\n"
             "   Print some information about this command line tool",
    "update": "Usage: esync update [--repo $REPO_NAME]\n"
              "   Update summary file of a repository, leave blank for sync all repo",
    "sync": "Usage: esync sync [--repo $REPO_NAME]\n"
            "   Sync file of a repository, leave blank for sync all repo",
    "ls": "Usage: esync ls\n"
          "   List all repositories",
    "add": "Usage: esync add --name $REPO_NAME --id $IDENTIFIER --type pool|posts --folder $FOLDER_PATH\n"
           "   Add a repository",
    "remove": "Usage: esync remove $REPO_NAME\n"
              "   Remove a repository",
    "rebuild": "Usage: esync rebuild --repo $REPO_NAME\n"
               "   If your .summary file is broken or missing, use rebuild command to make a valid .summary file.\n"
               "   But you have to update & sync the repo again.",
    "info": "Usage: esync info $REPO_NAME\n"
            "   List summary of a repository",
    "plsearch": "Usage: esync plsearch --title $SEARCH_TITLE\n"
                "   Search pools with the title",
    "login": "Usage: esync login --uid $USER_ID --key $API_KEY [--logout]\n"
             "   Use login command will give you the ability to use your e621 account's blacklist settings and so on.\n"
             "   You can logout anytime with --logout option",
    "rename": "* Usage: chdir --name $REPO_NAME --newfolder $NEW_FOLDER\n"
              "   Move repo storage folder to newfolder",
    "chdir": "Usage: chdir --name $REPO_NAME --newfolder $NEW_FOLDER\n"
             "   Move repo storage folder to newfolde"
}


# function to output error
def PrintError(msg: str) -> None:
    print(Fore.RED + msg + Style.RESET_ALL)


# this function will try to resume any uncompleted mission
def ResumeDownloadTasks(folder: str):
    resumed = False
    for item in listdir(folder):
        if item.endswith(".tasks.json"):
            if LoadFile(folder + "/" + item) != "[]":
                resumed = True
                extDownloader = AsyncDownloader()
                extDownloader.taskSummaryFilePath = folder
                extDownloader.LoadTasks(folder + "/" + item)
                print("Resuming %s ..." % item)
                extDownloader.FetchAllItems()
            else:
                os.remove(folder + "/" + item)
    if resumed:
        print("Folder %s resume complete" % folder)


# class for Fire library to use
class ESync():

    def help(self, command: str = ""):
        defaultHelp = "Usage: esync <command>\n" \
                      "    available commands:    about | add | info | login | ls | plsearch | rebuild | rm | sync | update | help\n" \
                      "    use esync help <command> to view help from each command"
        if command == "":
            print(defaultHelp)
            return
        if command not in commandHelp.keys():
            PrintError("Command %s not exists." % command)
        else:
            print(commandHelp[command])

    # update summary files
    def update(self, name: str = ""):
        beginAt = time.time()
        summaries = dict()
        updatedCount = dict()
        pair = LoadConfig().repositoryPair
        print("Updating repository summaries ...")
        # update .summary files
        if name == "":
            # load all repo name
            repos = pair.keys()
        else:
            if name in LoadConfig().repositoryPair.keys():
                repos = [name]
            else:
                PrintError("Repo \"%s\" not exists." % name)
                return
        for repoName in repos:
            try:
                # store original pic count in advance
                origCount = len(LoadSummary(pair[repoName]).downloadQueue)
                summary = manager.UpdateRepoSummaryFile(repoName)
                summaries[repoName] = summary
                updatedCount[repoName] = len(summary.downloadQueue) - origCount
            except RepoNotExistsException:
                PrintError("Repo \"%s\" not exists." % repoName)
        # display result as table
        table = ptt.PrettyTable(["Repo Name", "Type", "Identifier", "New"])
        table.align = "l"
        for repoName in summaries.keys():
            summary = summaries[repoName]
            table.add_row([
                repoName,
                summary.repoType,
                summary.repoIdentifier,
                updatedCount[repoName]
            ])
        print(table)
        print("Update complete in %s seconds." % int(time.time() - beginAt))

    def sync(self, name: str = ""):
        config = LoadConfig()
        if name == "":
            # sync all repository
            for repoName in config.repositoryPair.keys():
                print("Repo \"%s\" sync started." % repoName)
                ResumeDownloadTasks(config.repositoryPair[repoName])
                downloader.taskSummaryFilePath = config.repositoryPair[repoName]
                manager.SyncRepository(repoName=repoName)
                downloader.FetchAllItems()
                downloader.Clear()
        else:
            # sync only "repo"
            if name in config.repositoryPair.keys():
                print("Repo \"%s\" sync started." % name)
                ResumeDownloadTasks(config.repositoryPair[name])
                downloader.taskSummaryFilePath = config.repositoryPair[name]
                manager.SyncRepository(repoName=name)
                downloader.FetchAllItems()
                downloader.Clear()
            else:
                PrintError("Repo \"%s\" not exists." % name)
                return

    def ls(self):
        repos = LoadConfig().repositoryPair
        # beautify table output
        table = ptt.PrettyTable(["Repo Name", "Folder"])
        table.align = "l"
        for repoName in repos:
            table.add_row([repoName, repos[repoName]])
        print(table)

    def add(self, type: str, name: str, folder: str, id: str):
        if type != "pool" and type != "posts":
            PrintError("Repo type parameter \"--type\" must be either \"pool\" or \"posts\".")
            return
        InitRepo(repoName=name, repoFolder=folder, folderType=type, identifier=id)
        print("Added repo \"%s\"." % name)

    def rm(self, repo: str):
        if repo in LoadConfig().repositoryPair.keys():
            RemoveRepo(repoName=repo)
            print("Repo \"%s\" removed." % repo)
        else:
            PrintError("Repo \"%s\" not exists." % repo)
            return

    def info(self, repo: str):
        repos = LoadConfig().repositoryPair
        table = ptt.PrettyTable(["Repo Name", "Identifier", "Type", "Local", "Server", "Pinned", "Last Update"])
        table.align = "l"
        # assemble all repo information into a table
        if repo in repos.keys():
            summary = LoadSummary(repos[repo])
            # make table output
            table.add_row([
                repo,
                summary.repoIdentifier,
                summary.repoType,
                len(summary.fileMetadata),
                len(summary.downloadQueue),
                "Yes" if summary.pinned else "No",
                ConvertFloatTime(summary.updatedAt)
            ])
        else:
            PrintError("Repo \"%s\" not exists." % repo)
            return
        print(table)

    def plsearch(self, title: str):
        # load api token
        config = LoadConfig()
        poolApi = PoolApi()
        poolApi.loginParams = {"login": config.loginId, "api_key": config.apiToken}
        maxDescriptionLen = 50
        print("Query started ...")
        jsonResp = poolApi.Search(name_matches=title)
        table = ptt.PrettyTable(["Pool Id", "Pool Name", "Posts Count", "Description"])
        table.align = "l"
        for item in jsonResp:
            table.add_row([item["id"], item["name"], item["post_count"],
                           (item["description"][0:maxDescriptionLen - 4] + " ...")
                           if len(item["description"]) > maxDescriptionLen else item["description"]])
        print(table)

    def about(self):
        aboutMe = "The esync provided a more convenience way to sync your favourite pools/posts from e621.\n" + \
                  "This program distributed under GPLv3 license at https://github.com/FaolanWolf/EsixSync.\n" + \
                  "All online resources are provided by https://e621.net.\n"
        print(aboutMe)

    def rebuild(self, repo: str, type: str, id: str):
        if type != "pool" and type != "posts":
            PrintError("Repo type parameter \"--type\" must be either \"pool\" or \"posts\".")
            return
        RebuildSummary(repoName=repo, identifier=id, folderType=type)
        print("Rebuild repo \"%s\" complete." % repo)

    def login(self, uid: str = "", key: str = "", logout: bool = False):
        if logout:
            config = LoadConfig()
            config.loginId = None
            config.apiToken = None
            StoreConfig(config)
        else:
            if uid == "" or key == "":
                PrintError("You must have both uid and key to login.")
            else:
                config = LoadConfig()
                config.loginId = uid
                config.apiToken = key
                StoreConfig(config)

    def rename(self, name: str, newname: str):
        config = LoadConfig()
        if name in config.repositoryPair.keys():
            folder = config.repositoryPair[name]
            config.repositoryPair.pop(name)
            config.repositoryPair[newname] = folder
            StoreConfig(config)
            print("Repo %s successfully renamed to %s" % (name, newname))
        else:
            PrintError("Repo \"%s\" not exists." % name)
            return

    def chdir(self, name: str, newfolder: str):
        config = LoadConfig()
        if name in config.repositoryPair.keys():
            if path.exists(newfolder) and path.isdir(newfolder):
                folder = config.repositoryPair[name]
                config.repositoryPair[name] = newfolder
                StoreConfig()
                print("Update repo storage folder complete, please move all file from %s to %s" % (folder, newfolder))
        else:
            PrintError("Repo \"%s\" not exists." % name)
            return


'''
Usage: esync <command>
  available commands:    about | add | info | login | ls | plsearch | rebuild | rm | sync | update

Usage: esync about
    Print some information about this command line tool.

Usage: esync update [--repo $REPO_NAME]
    Update summary file of a repository, leave blank for sync all repo

Usage: esync sync [--repo $REPO_NAME]
    Sync file of a repository, leave blank for sync all repo
    
Usage: esync ls
    List all repositories.

Usage: esync add --name $REPO_NAME --id $IDENTIFIER --type pool|posts --folder $FOLDER_PATH
    Add a repository

Usage: esync remove $REPO_NAME
    Remove a repository

Usage: esync rebuild --repo $REPO_NAME
    If case you .summary file is broken, use rebuild command to make a valid .summary file.
    But you have to update & sync the repo again from begging

Usage: esync info $REPO_NAME
    List summary of a repository

Usage: esync plsearch --title $SEARCH_TITLE
    Search pools with the title
    
Usage: esync login --uid $USER_ID --key $API_KEY [--logout]
    Use login command will give you the ability to use your e621 account's blacklist settings and so on.
    You can logout anytime with --logout option

Usage: rename --name $OLD_NAME --newname $NEW_NAME
    Rename repo from name to newname
    
Usage: chdir --name $REPO_NAME --newfolder $NEW_FOLDER
    Move repo storage folder to newfolder
    
Usage: help
    List all commands you could use
'''
if __name__ == '__main__':
    downloader = AsyncDownloader()
    # use custom Downloader and StatusReporter implementation
    manager = RepoUpdateManager(downloader=downloader)
    # disable traceback
    sys.tracebacklimit = 0
    try:
        fire.Fire(ESync)
    except Exception as e:
        # log error
        print("")
        print(Fore.RED)
        print(e)
        print(Style.RESET_ALL)
        timespan = int(time.time())
        file = sys.path[0] + "exp"
