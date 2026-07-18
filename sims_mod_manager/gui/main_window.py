"""Top-level window: two tabs sharing one AppContext, plus the one-time
settings toggle and the once-per-session backup safety net."""
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QMessageBox, QTabWidget

from sims_mod_manager import config
from sims_mod_manager.core.backup import backup_mod_folders
from sims_mod_manager.core.installer import InstallResult, install_mod_file
from sims_mod_manager.core.settings_toggle import (
    SettingsToggleResult,
    enable_mods_and_script_mods,
)
from sims_mod_manager.core.store import ModStore
from sims_mod_manager.gui.activity_tab import ActivityTab
from sims_mod_manager.gui.find_tab import FindTab
from sims_mod_manager.gui.inbox_tab import InboxTab


class InstallCoordinator:
    def __init__(
        self,
        mods_dir: Path,
        staging_dir: Path,
        store: ModStore,
        sims4_dir: Path,
        backup_dir: Path,
    ):
        self._mods_dir = mods_dir
        self._staging_dir = staging_dir
        self._store = store
        self._sims4_dir = sims4_dir
        self._backup_dir = backup_dir
        self._backed_up_this_session = False

    def install(self, source_path: Path) -> InstallResult:
        if not self._backed_up_this_session:
            backup_mod_folders(self._sims4_dir, self._backup_dir)
            self._backed_up_this_session = True
        return install_mod_file(source_path, self._mods_dir, self._store, self._staging_dir)


@dataclass
class AppContext:
    staging_dir: Path
    downloads_dir: Path
    install_coordinator: InstallCoordinator
    store: ModStore


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sims 4 Mod Manager")
        self.resize(900, 600)

        store = ModStore(config.get_store_db_path())
        install_coordinator = InstallCoordinator(
            mods_dir=config.get_mods_dir(),
            staging_dir=config.get_staging_dir(),
            store=store,
            sims4_dir=config.get_sims4_dir(),
            backup_dir=config.get_backup_dir(),
        )
        context = AppContext(
            staging_dir=config.get_staging_dir(),
            downloads_dir=config.get_downloads_dir(),
            install_coordinator=install_coordinator,
            store=store,
        )

        tabs = QTabWidget()
        tabs.addTab(FindTab(context), "Find")
        inbox_tab = InboxTab(context)
        tabs.addTab(inbox_tab, "Inbox")
        self._inbox_tab = inbox_tab
        tabs.addTab(ActivityTab(context), "Activity")
        self.setCentralWidget(tabs)

        self._maybe_show_settings_reminder()

    def closeEvent(self, event) -> None:
        # InboxTab is a child widget (added via QTabWidget.addTab), and Qt
        # only delivers closeEvent to the top-level window being closed --
        # never to child widgets. So we reach into the tab explicitly here
        # to stop its background watcher thread cleanly whenever the real
        # top-level window closes.
        self._inbox_tab.shutdown()
        super().closeEvent(event)

    def _maybe_show_settings_reminder(self) -> None:
        result = enable_mods_and_script_mods(config.get_options_ini_path())
        if result == SettingsToggleResult.NEEDS_MANUAL_FALLBACK:
            QMessageBox.information(
                self,
                "One-time setup",
                "Open The Sims 4, go to Options > Game Options > Other, and enable "
                '"Enable Custom Content and Mods" and "Script Mods Allowed", '
                "then restart the game. You'll only need to do this once.",
            )
