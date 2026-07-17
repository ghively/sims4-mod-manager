"""Real filesystem paths used by the app. Core modules never import this --
they take Path arguments explicitly so they stay testable without touching
a real Sims 4 install."""
from pathlib import Path


def get_sims4_dir() -> Path:
    return Path.home() / "Documents" / "Electronic Arts" / "The Sims 4"


def get_mods_dir() -> Path:
    return get_sims4_dir() / "Mods"


def get_saves_dir() -> Path:
    return get_sims4_dir() / "Saves"


def get_tray_dir() -> Path:
    return get_sims4_dir() / "Tray"


def get_options_ini_path() -> Path:
    return get_sims4_dir() / "Options.ini"


def get_app_data_dir() -> Path:
    app_dir = Path.home() / "AppData" / "Local" / "SimsModManager"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_store_db_path() -> Path:
    return get_app_data_dir() / "store.db"


def get_backup_dir() -> Path:
    backup_dir = get_app_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_staging_dir() -> Path:
    staging_dir = get_app_data_dir() / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    return staging_dir


def get_downloads_dir() -> Path:
    return Path.home() / "Downloads"
