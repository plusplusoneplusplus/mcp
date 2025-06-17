from enum import Enum

class Ecosystem(Enum):
    MICROSOFT = "microsoft"
    GENERAL = "general"

    def __str__(self) -> str:
        return self.value

class OSType(Enum):
    WINDOWS = "windows"
    NON_WINDOWS = "non-windows"
    ALL = "all"

    def __str__(self) -> str:
        return self.value
