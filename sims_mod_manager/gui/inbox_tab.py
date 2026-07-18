"""Shows Downloads-folder candidates and lets the user install them with one click."""
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sims_mod_manager.core.watcher import DownloadsWatcher

_PATH_DATA_ROLE = 1000


class InboxTab(QWidget):
    _new_candidate = Signal(Path)

    def __init__(self, context):
        super().__init__()
        self._context = context

        self._list = QListWidget()
        install_button = QPushButton("Install selected")
        install_button.clicked.connect(self._on_install_clicked)
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Files ready to install:"))
        layout.addWidget(self._list)
        button_row = QHBoxLayout()
        button_row.addWidget(install_button)
        layout.addLayout(button_row)
        layout.addWidget(self._status_label)
        self.setLayout(layout)

        self._new_candidate.connect(self._add_candidate)
        self._watcher = DownloadsWatcher(
            context.downloads_dir, on_new_file=self._new_candidate.emit
        )
        self._watcher.start()

    def _add_candidate(self, path: Path) -> None:
        item = QListWidgetItem(path.name)
        item.setData(_PATH_DATA_ROLE, str(path))
        self._list.addItem(item)

    def _on_install_clicked(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        source_path = Path(item.data(_PATH_DATA_ROLE))
        try:
            result = self._context.install_coordinator.install(source_path)
        except Exception as exc:
            self._status_label.setText(
                f"Something went wrong installing this file: {exc}"
            )
            return
        if result.errors:
            self._status_label.setText("; ".join(result.errors))
        elif result.installed:
            self._status_label.setText(f"Installed {len(result.installed)} file(s).")
            self._list.takeItem(self._list.row(item))
        elif result.duplicates:
            self._status_label.setText("Already installed — skipped duplicate.")
            self._list.takeItem(self._list.row(item))

    def closeEvent(self, event) -> None:
        self._watcher.stop()
        super().closeEvent(event)
