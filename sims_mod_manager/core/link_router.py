"""Classifies a pasted URL so the Find tab knows whether it can download
directly or needs to hand off to the browser."""
from enum import Enum
from urllib.parse import urlparse

DIRECT_FILE_SUFFIXES = (".zip", ".rar", ".package", ".ts4script")


class LinkAction(Enum):
    DIRECT_DOWNLOAD = "direct_download"
    OPEN_IN_BROWSER = "open_in_browser"


def classify_link(url: str) -> LinkAction:
    path = urlparse(url).path.lower()
    if path.endswith(DIRECT_FILE_SUFFIXES):
        return LinkAction.DIRECT_DOWNLOAD
    return LinkAction.OPEN_IN_BROWSER
