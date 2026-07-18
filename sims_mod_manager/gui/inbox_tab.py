"""Shows Downloads-folder candidates and lets the user install them with one click."""
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sims_mod_manager.core.watcher import DownloadsWatcher
from sims_mod_manager.gui.install_worker import InstallWorker

_PATH_DATA_ROLE = 1000


class InboxTab(QWidget):
    _new_candidate = Signal(Path)

    def __init__(self, context):
        super().__init__()
        self._context = context

        self._list = QListWidget()
        self._install_button = QPushButton("Install selected")
        self._install_button.clicked.connect(self._on_install_clicked)
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate/busy indicator
        self._progress_bar.hide()

        self._worker = None
        self._pending_item = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Files ready to install:"))
        layout.addWidget(self._list)
        button_row = QHBoxLayout()
        button_row.addWidget(self._install_button)
        layout.addLayout(button_row)
        layout.addWidget(self._progress_bar)
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

        self._pending_item = item
        self._worker = InstallWorker(self._context.install_coordinator, source_path)
        self._worker.succeeded.connect(self._on_install_succeeded)
        self._worker.failed.connect(self._on_install_failed)
        self._install_button.setEnabled(False)
        self._progress_bar.show()
        self._worker.start()

    def _on_install_succeeded(self, result) -> None:
        item = self._pending_item
        if result.errors:
            self._status_label.setText("; ".join(result.errors))
        elif result.installed:
            self._status_label.setText(f"Installed {len(result.installed)} file(s).")
            self._list.takeItem(self._list.row(item))
        elif result.duplicates:
            self._status_label.setText("Already installed — skipped duplicate.")
            self._list.takeItem(self._list.row(item))
        self._pending_item = None
        self._progress_bar.hide()
        self._install_button.setEnabled(True)

    def _on_install_failed(self, message: str) -> None:
        self._status_label.setText(
            f"Something went wrong installing this file: {message}"
        )
        self._pending_item = None
        self._progress_bar.hide()
        self._install_button.setEnabled(True)

    def shutdown(self) -> None:
        """Stop the background watcher thread cleanly.

        `MainWindow` calls this from its own `closeEvent`, since Qt only
        delivers `closeEvent` to the top-level window being closed -- never
        to child widgets nested inside it (like this tab, added via
        `QTabWidget.addTab`). See `MainWindow.closeEvent`.
        """
        self._watcher.stop()

    def closeEvent(self, event) -> None:
        # Unreachable in the real app (InboxTab is always a child widget,
        # and child widgets never receive closeEvent), but kept for
        # correctness if InboxTab is ever used as a top-level window in
        # isolation (e.g. a test).
        self._watcher.stop()
        super().closeEvent(event)
