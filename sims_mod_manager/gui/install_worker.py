"""Runs an install on a background thread so the GUI stays responsive."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal


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
