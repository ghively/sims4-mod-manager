"""Runs an install on a background thread so the GUI stays responsive."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from sims_mod_manager.core.downloader import DownloadError, download_file


class InstallWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, install_coordinator, source_path: Path):
        super().__init__()
        self._install_coordinator = install_coordinator
        self._source_path = source_path

    def run(self) -> None:
        try:
            result = self._install_coordinator.install(self._source_path)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)


class DownloadAndInstallWorker(QThread):
    """Downloads a direct-link file and installs it, both on a background thread.

    Used by the paste-a-link flow, where the download itself (large Sims 4
    mod packs, hundreds of MB) is often the slowest, highest-variance step
    and must not block the GUI thread.
    """

    succeeded = Signal(object)
    download_failed = Signal(str)
    failed = Signal(str)

    def __init__(self, install_coordinator, url: str, staging_dir: Path):
        super().__init__()
        self._install_coordinator = install_coordinator
        self._url = url
        self._staging_dir = staging_dir

    def run(self) -> None:
        try:
            downloaded_path = download_file(self._url, self._staging_dir)
        except DownloadError as exc:
            self.download_failed.emit(str(exc))
            return
        try:
            result = self._install_coordinator.install(downloaded_path)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)
