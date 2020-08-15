class PoolNotExistsException(Exception):
    def __init__(self, poolId: int):
        Exception.__init__(self, "Pool id '%s' does not exists." % poolId)


class RepoNotExistsException(Exception):
    def __init__(self, repoName: str):
        Exception.__init__(self, "Repository '%s' does not exists." % repoName)


class RepoDuplicatedException(Exception):
    def __init__(self, repoName: str, repoFolder: str):
        Exception.__init__(self, "Repository '%s:%s' already exists." % (repoName, repoFolder))


class LoadConfigException(Exception):
    def __init__(self, configPath: str):
        Exception.__init__(self, "Config '%s' failed to load." % (configPath))


class SummaryFileMissingException(Exception):
    def __init__(self, summaryPath: str):
        Exception.__init__(self, "Summary file '%s' failed to load." % (summaryPath))
