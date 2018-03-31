from enum import Enum


class TorrentStates(Enum):
    NOT_STARTED = 0
    STARTED = 1
    PAUSED = 2
    DOWNLOADED = 3
