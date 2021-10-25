from scanomatic.io.app_config import Config
from scanomatic.io.paths import Paths


class PathUser:
    def __init__(self):
        self._path = Paths()


class AppConfigUser:
    def __init__(self):
        self._appConfig = Config()


class PathAndAppConfigUser:
    def __init__(self):
        self._path = Paths()
        self._appConfig = Config()
