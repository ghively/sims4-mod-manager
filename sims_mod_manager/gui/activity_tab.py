"""Read-only view of what's been installed, sourced from the local ModStore."""
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

_COLUMNS = ("Filename", "Category", "Source", "Installed Path", "Installed At")


class ActivityTab(QWidget):
    def __init__(self, context):
        super().__init__()
        self._context = context

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)

        layout = QVBoxLayout()
        layout.addWidget(refresh_button)
        layout.addWidget(self._table)
        self.setLayout(layout)

        self.refresh()

    def refresh(self) -> None:
        entries = self._context.store.get_activity_log()
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self._table.setItem(row, 0, QTableWidgetItem(entry["filename"]))
            self._table.setItem(row, 1, QTableWidgetItem(entry["category"]))
            self._table.setItem(row, 2, QTableWidgetItem(entry["source"]))
            self._table.setItem(row, 3, QTableWidgetItem(entry["installed_path"]))
            self._table.setItem(row, 4, QTableWidgetItem(entry["installed_at"]))

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)
