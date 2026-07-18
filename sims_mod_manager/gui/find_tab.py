"""Search box + site toggle + paste-a-link box."""
import webbrowser

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sims_mod_manager.core.downloader import DownloadError, download_file
from sims_mod_manager.core.link_router import LinkAction, classify_link
from sims_mod_manager.core.search_launcher import (
    SITE_BOTH,
    SITE_CURSEFORGE,
    SITE_MODTHESIMS,
    open_search,
)


class FindTab(QWidget):
    def __init__(self, context):
        super().__init__()
        self._context = context

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search for a mod...")
        self._site_selector = QComboBox()
        self._site_selector.addItem("Both sites", SITE_BOTH)
        self._site_selector.addItem("CurseForge", SITE_CURSEFORGE)
        self._site_selector.addItem("ModTheSims", SITE_MODTHESIMS)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self._on_search)

        self._link_box = QLineEdit()
        self._link_box.setPlaceholderText("Or paste a mod link here...")
        go_button = QPushButton("Go")
        go_button.clicked.connect(self._on_link_submitted)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)

        search_row = QHBoxLayout()
        search_row.addWidget(self._search_box)
        search_row.addWidget(self._site_selector)
        search_row.addWidget(search_button)

        link_row = QHBoxLayout()
        link_row.addWidget(self._link_box)
        link_row.addWidget(go_button)

        layout = QVBoxLayout()
        layout.addLayout(search_row)
        layout.addLayout(link_row)
        layout.addWidget(self._status_label)
        layout.addStretch()
        self.setLayout(layout)

    def _on_search(self) -> None:
        query = self._search_box.text().strip()
        if not query:
            return
        site = self._site_selector.currentData()
        open_search(query, site)
        self._status_label.setText(f"Opened search results for '{query}'.")

    def _on_link_submitted(self) -> None:
        url = self._link_box.text().strip()
        if not url:
            return

        if classify_link(url) == LinkAction.OPEN_IN_BROWSER:
            webbrowser.open(url)
            self._status_label.setText(
                "Opened in your browser — download it there and I'll catch it automatically."
            )
            return

        try:
            downloaded_path = download_file(url, self._context.staging_dir)
        except DownloadError as exc:
            self._status_label.setText(str(exc))
            return

        result = self._context.install_coordinator.install(downloaded_path)
        self._status_label.setText(_describe_install_result(result))


def _describe_install_result(result) -> str:
    if result.errors:
        return "; ".join(result.errors)
    if result.installed:
        return f"Installed {len(result.installed)} file(s)."
    if result.duplicates:
        return "Already installed — skipped duplicate."
    return "Nothing to install."
