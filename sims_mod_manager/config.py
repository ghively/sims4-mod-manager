"""Real filesystem paths used by the app. Core modules never import this --
they take Path arguments explicitly so they stay testable without touching
a real Sims 4 install."""
import ctypes
from ctypes import wintypes
from pathlib import Path

# FOLDERID_Documents -- the Windows Known Folder GUID for the (possibly
# redirected, e.g. via OneDrive Known Folder Move) "Documents" folder.
_FOLDERID_DOCUMENTS = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"

# FOLDERID_Downloads -- the Windows Known Folder GUID for the (possibly
# redirected, e.g. via OneDrive Known Folder Move) "Downloads" folder.
_FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"


def _query_known_folder_path(folder_id: str) -> str:
    """Call SHGetKnownFolderPath for `folder_id` and return the resolved path.

    Kept as a small, separate function so tests can monkeypatch it directly
    instead of reaching into ctypes.windll. Raises OSError if the underlying
    call fails for any reason.
    """
    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_byte * 8),
        ]

    guid_struct = GUID()
    result = ctypes.windll.ole32.CLSIDFromString(
        ctypes.c_wchar_p(folder_id), ctypes.byref(guid_struct)
    )
    if result != 0:
        raise OSError(f"CLSIDFromString failed for {folder_id!r} (hresult={result:#x})")

    path_ptr = ctypes.c_wchar_p()
    hresult = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(guid_struct), 0, None, ctypes.byref(path_ptr)
    )
    if hresult != 0 or not path_ptr.value:
        raise OSError(f"SHGetKnownFolderPath failed for {folder_id!r} (hresult={hresult:#x})")

    try:
        path = path_ptr.value
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)

    return path


def get_documents_dir() -> Path:
    """Resolve the real Windows "Documents" known folder.

    This accounts for redirection (e.g. OneDrive Known Folder Move), which
    can place Documents somewhere other than %USERPROFILE%\\Documents. Falls
    back to Path.home() / "Documents" if the Known Folder API call fails, so
    the app never hard-crashes over this.
    """
    try:
        return Path(_query_known_folder_path(_FOLDERID_DOCUMENTS))
    except OSError:
        return Path.home() / "Documents"


def get_downloads_dir() -> Path:
    """Resolve the real Windows "Downloads" known folder.

    This accounts for redirection (e.g. OneDrive Known Folder Move), which
    can place Downloads somewhere other than %USERPROFILE%\\Downloads. Falls
    back to Path.home() / "Downloads" if the Known Folder API call fails, so
    the app never hard-crashes over this.
    """
    try:
        return Path(_query_known_folder_path(_FOLDERID_DOWNLOADS))
    except OSError:
        return Path.home() / "Downloads"


def get_sims4_dir() -> Path:
    return get_documents_dir() / "Electronic Arts" / "The Sims 4"


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
