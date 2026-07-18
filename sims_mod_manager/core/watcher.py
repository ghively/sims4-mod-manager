"""Polls the Downloads folder for new files that look like Sims 4 mods and
reports each one exactly once via a callback. Runs in a background thread
only while the app window is open -- there is no persistent service."""
import threading
import time
from pathlib import Path
from typing import Callable

MOD_FILE_SUFFIXES = (".zip", ".rar", ".package", ".ts4script")


class DownloadsWatcher:
    def __init__(
        self,
        downloads_dir: Path,
        on_new_file: Callable[[Path], None],
        poll_interval_seconds: float = 2.0,
    ):
        self._downloads_dir = downloads_dir
        self._on_new_file = on_new_file
        self._poll_interval_seconds = poll_interval_seconds
        self._seen: set[Path] = set()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._seen = self._scan()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_interval_seconds * 2)

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll_interval_seconds):
            current = self._scan()
            for new_path in sorted(current - self._seen):
                self._on_new_file(new_path)
            self._seen = current

    def _scan(self) -> set[Path]:
        if not self._downloads_dir.exists():
            return set()
        return {
            path
            for path in self._downloads_dir.iterdir()
            if path.is_file() and path.suffix.lower() in MOD_FILE_SUFFIXES
        }
