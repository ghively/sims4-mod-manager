# Sims 4 Mod Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-process Windows desktop app (Python + PySide6, packaged as one `.exe`) that lets a non-technical user search for Sims 4 mods on ModTheSims/CurseForge and turns a downloaded mod file into a correctly-installed one with minimal clicks.

**Architecture:** One Python package (`sims_mod_manager`) split into a framework-agnostic `core/` (pure logic: extract, flatten, categorize, dedupe, backup, settings toggle, search URL building, link classification, downloading, folder watching — all unit-testable with `pytest` and no GUI dependency) and a thin `gui/` layer (PySide6 widgets that call `core/` functions). A `MainWindow` wires up an `AppContext` shared by two tabs (Find, Inbox) and an `InstallCoordinator` that adds the once-per-session backup and centralizes the install call.

**Tech Stack:** Python 3.11+, PySide6 (Qt GUI), `requests` (direct-link downloads), `rarfile` (optional `.rar` support, degrades gracefully if the system has no `unrar`/`unar` binary), stdlib `zipfile`/`sqlite3`/`hashlib`, `pytest` (tests), `PyInstaller` (packaging).

## Global Constraints

- Windows-only; all real paths are under `Documents\Electronic Arts\The Sims 4` (`Mods`, `Saves`, `Tray`, `Options.ini`).
- Single process, no background service, no browser extension — the Downloads watcher only runs while the app window is open.
- No CurseForge API integration and no automated scraping/downloading from ModTheSims — both are search-launcher only (open a pre-filled search in the default browser). The app only ever downloads programmatically from a direct file URL (path ends in `.zip`/`.rar`/`.package`/`.ts4script`) or from files the user already has locally.
- Every installed file must land at most one folder deep under `Mods/` (the game's hard requirement).
- Never silently overwrite, drop, or lose a file. Every failure path either surfaces an error in the UI/log or falls back to an explicit manual step (never a silent no-op that looks like success).
- No automated GUI tests — `core/*.py` gets full `pytest` coverage; `gui/*.py` is verified manually (per the design spec's testing approach).
- `docs/superpowers/specs/2026-07-17-sims-mod-manager-design.md` is the source spec — every section of it is covered by a task below.

---

### Task 1: Project scaffolding & config module

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pytest.ini`
- Create: `sims_mod_manager/__init__.py`
- Create: `sims_mod_manager/core/__init__.py`
- Create: `sims_mod_manager/gui/__init__.py`
- Create: `sims_mod_manager/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `config.get_sims4_dir() -> Path`, `config.get_mods_dir() -> Path`, `config.get_saves_dir() -> Path`, `config.get_tray_dir() -> Path`, `config.get_options_ini_path() -> Path`, `config.get_app_data_dir() -> Path`, `config.get_store_db_path() -> Path`, `config.get_backup_dir() -> Path`, `config.get_staging_dir() -> Path`, `config.get_downloads_dir() -> Path` — used by every later task that needs a real filesystem location.

- [ ] **Step 1: Create dependency and pytest config files**

`requirements.txt`:
```
PySide6>=6.6
requests>=2.31
rarfile>=4.1
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=7.4
pyinstaller>=6.3
```

`pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 2: Create empty package init files**

Create `sims_mod_manager/__init__.py`, `sims_mod_manager/core/__init__.py`, `sims_mod_manager/gui/__init__.py`, all empty.

- [ ] **Step 3: Write the failing test**

`tests/test_config.py`:
```python
from sims_mod_manager import config


def test_mods_dir_is_under_sims4_dir():
    assert config.get_mods_dir() == config.get_sims4_dir() / "Mods"


def test_saves_and_tray_dirs_are_under_sims4_dir():
    assert config.get_saves_dir() == config.get_sims4_dir() / "Saves"
    assert config.get_tray_dir() == config.get_sims4_dir() / "Tray"


def test_options_ini_path_is_under_sims4_dir():
    assert config.get_options_ini_path() == config.get_sims4_dir() / "Options.ini"


def test_sims4_dir_matches_documents_electronic_arts_layout():
    sims4_dir = config.get_sims4_dir()
    assert sims4_dir.parts[-3:] == ("Documents", "Electronic Arts", "The Sims 4")


def test_app_data_dir_is_created(tmp_path, monkeypatch):
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path)
    app_dir = config.get_app_data_dir()
    assert app_dir.exists()
    assert app_dir == tmp_path / "AppData" / "Local" / "SimsModManager"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.config'` (or import error), since `config.py` doesn't exist yet.

- [ ] **Step 5: Write the implementation**

`sims_mod_manager/config.py`:
```python
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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini sims_mod_manager tests/test_config.py
git commit -m "feat: add project scaffolding and config module"
```

---

### Task 2: Categorizer

**Files:**
- Create: `sims_mod_manager/core/categorizer.py`
- Test: `tests/test_categorizer.py`

**Interfaces:**
- Produces: `CATEGORY_CAS`, `CATEGORY_BUILD_BUY`, `CATEGORY_GAMEPLAY`, `CATEGORY_SCRIPT`, `CATEGORY_UNCATEGORIZED` (str constants), `categorize_file(file_path: Path) -> str` — used by Task 6 (installer).

- [ ] **Step 1: Write the failing test**

`tests/test_categorizer.py`:
```python
from pathlib import Path

from sims_mod_manager.core.categorizer import (
    CATEGORY_BUILD_BUY,
    CATEGORY_CAS,
    CATEGORY_GAMEPLAY,
    CATEGORY_SCRIPT,
    CATEGORY_UNCATEGORIZED,
    categorize_file,
)


def test_ts4script_is_always_script_category():
    assert categorize_file(Path("SomeMod/whatever.ts4script")) == CATEGORY_SCRIPT


def test_hair_package_is_cas():
    assert categorize_file(Path("MaxisMatch_ToddlerHair.package")) == CATEGORY_CAS


def test_furniture_package_is_build_buy():
    assert categorize_file(Path("ModernFurniture_Set.package")) == CATEGORY_BUILD_BUY


def test_trait_package_is_gameplay():
    assert categorize_file(Path("NewTrait_Overhaul.package")) == CATEGORY_GAMEPLAY


def test_unrecognized_package_is_uncategorized():
    assert categorize_file(Path("xyz123.package")) == CATEGORY_UNCATEGORIZED


def test_keyword_match_in_parent_folder_name_counts():
    assert categorize_file(Path("Downloads/Hair Pack/file01.package")) == CATEGORY_CAS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_categorizer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.categorizer'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/categorizer.py`:
```python
"""Assigns a Sims 4 mod file to one of a fixed set of category folders."""
from pathlib import Path

CATEGORY_CAS = "CAS"
CATEGORY_BUILD_BUY = "Build-Buy"
CATEGORY_GAMEPLAY = "Gameplay"
CATEGORY_SCRIPT = "Script"
CATEGORY_UNCATEGORIZED = "Uncategorized"

ALL_CATEGORIES = (
    CATEGORY_CAS,
    CATEGORY_BUILD_BUY,
    CATEGORY_GAMEPLAY,
    CATEGORY_SCRIPT,
    CATEGORY_UNCATEGORIZED,
)

_CAS_KEYWORDS = (
    "hair", "skin", "eye", "eyes", "makeup", "cas", "clothing", "outfit",
    "accessor", "tattoo", "eyebrow", "eyelash",
)
_BUILD_BUY_KEYWORDS = (
    "build", "buy", "furniture", "object", "wallpaper", "floor", "deco",
    "curtain", "rug", "lighting",
)
_GAMEPLAY_KEYWORDS = (
    "gameplay", "trait", "career", "overhaul", "tuning", "interaction",
)


def categorize_file(file_path: Path) -> str:
    if file_path.suffix.lower() == ".ts4script":
        return CATEGORY_SCRIPT

    haystack = " ".join(part.lower() for part in (file_path.stem, *file_path.parts))

    if any(keyword in haystack for keyword in _CAS_KEYWORDS):
        return CATEGORY_CAS
    if any(keyword in haystack for keyword in _BUILD_BUY_KEYWORDS):
        return CATEGORY_BUILD_BUY
    if any(keyword in haystack for keyword in _GAMEPLAY_KEYWORDS):
        return CATEGORY_GAMEPLAY

    return CATEGORY_UNCATEGORIZED
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_categorizer.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/categorizer.py tests/test_categorizer.py
git commit -m "feat: add mod file categorizer"
```

---

### Task 3: Flattener (find mod files regardless of nesting)

**Files:**
- Create: `sims_mod_manager/core/flattener.py`
- Test: `tests/test_flattener.py`

**Interfaces:**
- Produces: `find_mod_files(staging_dir: Path) -> list[Path]` — used by Task 6 (installer).

- [ ] **Step 1: Write the failing test**

`tests/test_flattener.py`:
```python
from sims_mod_manager.core.flattener import find_mod_files


def test_finds_mod_files_at_any_depth(tmp_path):
    (tmp_path / "top.package").write_bytes(b"x")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (nested / "deep.ts4script").write_bytes(b"x")

    found = find_mod_files(tmp_path)

    assert found == sorted([tmp_path / "top.package", nested / "deep.ts4script"])


def test_ignores_non_mod_files(tmp_path):
    (tmp_path / "readme.txt").write_bytes(b"x")
    (tmp_path / "preview.jpg").write_bytes(b"x")

    assert find_mod_files(tmp_path) == []


def test_empty_directory_returns_empty_list(tmp_path):
    assert find_mod_files(tmp_path) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_flattener.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.flattener'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/flattener.py`:
```python
"""Finds installable Sims 4 mod files regardless of how deeply they're
nested inside an extracted archive."""
from pathlib import Path

MOD_FILE_SUFFIXES = (".package", ".ts4script")


def find_mod_files(staging_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in staging_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in MOD_FILE_SUFFIXES
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_flattener.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/flattener.py tests/test_flattener.py
git commit -m "feat: add mod file flattener/finder"
```

---

### Task 4: Dedupe hashing + local Store

**Files:**
- Create: `sims_mod_manager/core/dedupe.py`
- Create: `sims_mod_manager/core/store.py`
- Test: `tests/test_dedupe.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Produces: `hash_file(file_path: Path) -> str`; `class ModStore: __init__(self, db_path: Path)`, `is_duplicate(self, file_hash: str) -> bool`, `record_install(self, source: str, filename: str, category: str, file_hash: str, installed_path: str) -> None`, `get_activity_log(self) -> list[dict]`, `close(self) -> None` — used by Task 6 (installer) and Task 13 (GUI scaffold).

- [ ] **Step 1: Write the failing tests**

`tests/test_dedupe.py`:
```python
import hashlib

from sims_mod_manager.core.dedupe import hash_file


def test_hash_matches_direct_sha256(tmp_path):
    file_path = tmp_path / "sample.package"
    file_path.write_bytes(b"hello world")

    assert hash_file(file_path) == hashlib.sha256(b"hello world").hexdigest()


def test_different_content_gives_different_hash(tmp_path):
    file_a = tmp_path / "a.package"
    file_b = tmp_path / "b.package"
    file_a.write_bytes(b"content a")
    file_b.write_bytes(b"content b")

    assert hash_file(file_a) != hash_file(file_b)
```

`tests/test_store.py`:
```python
from sims_mod_manager.core.store import ModStore


def test_is_duplicate_false_before_any_record(tmp_path):
    store = ModStore(tmp_path / "store.db")
    assert store.is_duplicate("abc123") is False
    store.close()


def test_is_duplicate_true_after_record(tmp_path):
    store = ModStore(tmp_path / "store.db")
    store.record_install(
        source="C:/Downloads/mod.zip",
        filename="mod.package",
        category="CAS",
        file_hash="abc123",
        installed_path="C:/Mods/CAS/mod.package",
    )
    assert store.is_duplicate("abc123") is True
    store.close()


def test_activity_log_contains_recorded_install(tmp_path):
    store = ModStore(tmp_path / "store.db")
    store.record_install(
        source="C:/Downloads/mod.zip",
        filename="mod.package",
        category="CAS",
        file_hash="abc123",
        installed_path="C:/Mods/CAS/mod.package",
    )
    log = store.get_activity_log()
    assert len(log) == 1
    assert log[0]["filename"] == "mod.package"
    assert log[0]["category"] == "CAS"
    store.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dedupe.py tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError` for both `sims_mod_manager.core.dedupe` and `sims_mod_manager.core.store`

- [ ] **Step 3: Write the implementations**

`sims_mod_manager/core/dedupe.py`:
```python
"""Content-hashing for duplicate mod detection."""
import hashlib
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024


def hash_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        while chunk := handle.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()
```

`sims_mod_manager/core/store.py`:
```python
"""Local SQLite-backed record of installed mod files, used for duplicate
detection and the in-app activity log."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ModStore:
    def __init__(self, db_path: Path):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS installed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT NOT NULL,
                filename TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                installed_path TEXT NOT NULL,
                installed_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_hash ON installed_files(file_hash)"
        )
        self._conn.commit()

    def is_duplicate(self, file_hash: str) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM installed_files WHERE file_hash = ? LIMIT 1", (file_hash,)
        )
        return cursor.fetchone() is not None

    def record_install(
        self, source: str, filename: str, category: str, file_hash: str, installed_path: str
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO installed_files
                (file_hash, filename, category, source, installed_path, installed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file_hash,
                filename,
                category,
                source,
                installed_path,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def get_activity_log(self) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT filename, category, source, installed_path, installed_at "
            "FROM installed_files ORDER BY installed_at DESC"
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dedupe.py tests/test_store.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/dedupe.py sims_mod_manager/core/store.py tests/test_dedupe.py tests/test_store.py
git commit -m "feat: add file hashing and local install store"
```

---

### Task 5: Extractor

**Files:**
- Create: `sims_mod_manager/core/extractor.py`
- Test: `tests/test_extractor.py`

**Interfaces:**
- Produces: `class ExtractionError(Exception)`, `extract_archive(archive_path: Path, dest_dir: Path) -> None` — used by Task 6 (installer).

- [ ] **Step 1: Write the failing test**

`tests/test_extractor.py`:
```python
import zipfile

import pytest

import sims_mod_manager.core.extractor as extractor
from sims_mod_manager.core.extractor import ExtractionError, extract_archive


def _make_zip(zip_path, files):
    with zipfile.ZipFile(zip_path, "w") as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)


def test_extracts_nested_zip_contents(tmp_path):
    zip_path = tmp_path / "mod.zip"
    _make_zip(zip_path, {"folder/inner/mod.package": "data"})
    dest_dir = tmp_path / "out"

    extract_archive(zip_path, dest_dir)

    assert (dest_dir / "folder" / "inner" / "mod.package").read_text() == "data"


def test_corrupt_zip_raises_extraction_error(tmp_path):
    zip_path = tmp_path / "broken.zip"
    zip_path.write_bytes(b"not a real zip file")
    dest_dir = tmp_path / "out"

    with pytest.raises(ExtractionError):
        extract_archive(zip_path, dest_dir)


def test_unsupported_suffix_raises_extraction_error(tmp_path):
    archive_path = tmp_path / "mod.7z"
    archive_path.write_bytes(b"whatever")
    dest_dir = tmp_path / "out"

    with pytest.raises(ExtractionError):
        extract_archive(archive_path, dest_dir)


def test_rar_without_backend_raises_extraction_error(tmp_path, monkeypatch):
    monkeypatch.setattr(extractor, "rarfile", None)
    archive_path = tmp_path / "mod.rar"
    archive_path.write_bytes(b"whatever")
    dest_dir = tmp_path / "out"

    with pytest.raises(ExtractionError, match="manually"):
        extract_archive(archive_path, dest_dir)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.extractor'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/extractor.py`:
```python
"""Extracts downloaded mod archives into a staging directory."""
import zipfile
from pathlib import Path

try:
    import rarfile
except ImportError:  # rarfile package not installed
    rarfile = None


class ExtractionError(Exception):
    """Raised when an archive can't be extracted."""


def extract_archive(archive_path: Path, dest_dir: Path) -> None:
    suffix = archive_path.suffix.lower()
    dest_dir.mkdir(parents=True, exist_ok=True)

    if suffix == ".zip":
        _extract_zip(archive_path, dest_dir)
    elif suffix == ".rar":
        _extract_rar(archive_path, dest_dir)
    else:
        raise ExtractionError(f"Unsupported archive format: {suffix}")


def _extract_zip(archive_path: Path, dest_dir: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(dest_dir)
    except zipfile.BadZipFile as exc:
        raise ExtractionError(
            f"Could not open {archive_path.name}: not a valid zip file"
        ) from exc


def _extract_rar(archive_path: Path, dest_dir: Path) -> None:
    if rarfile is None:
        raise ExtractionError(
            f"Could not open {archive_path.name}: RAR extraction isn't available on "
            "this machine. Please extract it manually and drop the contents into the Inbox."
        )
    try:
        with rarfile.RarFile(archive_path) as archive:
            archive.extractall(dest_dir)
    except rarfile.Error as exc:
        raise ExtractionError(f"Could not open {archive_path.name}: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_extractor.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/extractor.py tests/test_extractor.py
git commit -m "feat: add archive extractor with graceful rar fallback"
```

---

### Task 6: Installer orchestrator

**Files:**
- Create: `sims_mod_manager/core/installer.py`
- Test: `tests/test_installer.py`

**Interfaces:**
- Consumes: `categorize_file` (Task 2), `find_mod_files` (Task 3), `hash_file` + `ModStore` (Task 4), `ExtractionError` + `extract_archive` (Task 5).
- Produces: `@dataclass InstallResult(installed: list[Path], duplicates: list[Path], errors: list[str])`, `install_mod_file(source_path: Path, mods_dir: Path, store: ModStore, staging_dir: Path) -> InstallResult` — used by Task 13 (GUI scaffold's `InstallCoordinator`).

- [ ] **Step 1: Write the failing test**

`tests/test_installer.py`:
```python
import zipfile

from sims_mod_manager.core.installer import install_mod_file
from sims_mod_manager.core.store import ModStore


def _make_zip(zip_path, files):
    with zipfile.ZipFile(zip_path, "w") as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)


def test_installs_package_from_zip(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    zip_path = downloads_dir / "hair_mod.zip"
    _make_zip(zip_path, {"HairMod/hair.package": "data"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(zip_path, mods_dir, store, staging_dir)

    assert len(result.installed) == 1
    assert result.installed[0].name == "hair.package"
    assert result.installed[0].exists()
    assert result.installed[0].parent.parent == mods_dir
    assert result.errors == []
    store.close()


def test_installing_same_zip_twice_is_flagged_as_duplicate(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    zip_path = downloads_dir / "hair_mod.zip"
    _make_zip(zip_path, {"HairMod/hair.package": "data"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    first = install_mod_file(zip_path, mods_dir, store, staging_dir)
    second = install_mod_file(zip_path, mods_dir, store, staging_dir)

    assert len(first.installed) == 1
    assert second.installed == []
    assert len(second.duplicates) == 1
    store.close()


def test_installs_direct_ts4script_file(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    script_path = downloads_dir / "gameplay.ts4script"
    script_path.write_bytes(b"script bytes")

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(script_path, mods_dir, store, staging_dir)

    assert len(result.installed) == 1
    assert result.installed[0].parent.name == "Script"
    store.close()


def test_unrecognized_file_type_produces_error(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    text_path = downloads_dir / "notes.txt"
    text_path.write_bytes(b"not a mod")

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(text_path, mods_dir, store, staging_dir)

    assert result.installed == []
    assert len(result.errors) == 1
    store.close()


def test_archive_with_no_mod_files_produces_error(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    zip_path = downloads_dir / "readme_only.zip"
    _make_zip(zip_path, {"readme.txt": "just a readme"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(zip_path, mods_dir, store, staging_dir)

    assert result.installed == []
    assert len(result.errors) == 1
    store.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.installer'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/installer.py`:
```python
"""Orchestrates the full install pipeline for a single downloaded item:
extract (if needed) -> find mod files -> categorize -> dedupe -> copy into
Mods -> record."""
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from sims_mod_manager.core.categorizer import categorize_file
from sims_mod_manager.core.dedupe import hash_file
from sims_mod_manager.core.extractor import ExtractionError, extract_archive
from sims_mod_manager.core.flattener import find_mod_files
from sims_mod_manager.core.store import ModStore

_ARCHIVE_SUFFIXES = (".zip", ".rar")
_DIRECT_MOD_SUFFIXES = (".package", ".ts4script")


@dataclass
class InstallResult:
    installed: list[Path] = field(default_factory=list)
    duplicates: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def install_mod_file(
    source_path: Path, mods_dir: Path, store: ModStore, staging_dir: Path
) -> InstallResult:
    result = InstallResult()
    suffix = source_path.suffix.lower()

    if suffix in _ARCHIVE_SUFFIXES:
        item_staging_dir = staging_dir / source_path.stem
        try:
            extract_archive(source_path, item_staging_dir)
        except ExtractionError as exc:
            result.errors.append(str(exc))
            return result
        mod_files = find_mod_files(item_staging_dir)
    elif suffix in _DIRECT_MOD_SUFFIXES:
        mod_files = [source_path]
    else:
        result.errors.append(f"Not a recognized mod file: {source_path.name}")
        return result

    if not mod_files:
        result.errors.append(f"No .package or .ts4script files found in {source_path.name}")
        return result

    for mod_file in mod_files:
        file_hash = hash_file(mod_file)
        if store.is_duplicate(file_hash):
            result.duplicates.append(mod_file)
            continue

        category = categorize_file(mod_file)
        category_dir = mods_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        target_path = category_dir / mod_file.name
        shutil.copy2(mod_file, target_path)

        store.record_install(
            source=str(source_path),
            filename=mod_file.name,
            category=category,
            file_hash=file_hash,
            installed_path=str(target_path),
        )
        result.installed.append(target_path)

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/installer.py tests/test_installer.py
git commit -m "feat: add install pipeline orchestrator"
```

---

### Task 7: Backup

**Files:**
- Create: `sims_mod_manager/core/backup.py`
- Test: `tests/test_backup.py`

**Interfaces:**
- Produces: `backup_mod_folders(sims4_dir: Path, backup_root: Path) -> Path` — used by Task 13 (GUI scaffold's `InstallCoordinator`).

- [ ] **Step 1: Write the failing test**

`tests/test_backup.py`:
```python
import zipfile

from sims_mod_manager.core.backup import backup_mod_folders


def test_backup_includes_mods_and_saves_files(tmp_path):
    sims4_dir = tmp_path / "Sims4"
    (sims4_dir / "Mods").mkdir(parents=True)
    (sims4_dir / "Mods" / "foo.package").write_bytes(b"x")
    (sims4_dir / "Saves").mkdir(parents=True)
    (sims4_dir / "Saves" / "save1.save").write_bytes(b"x")
    backup_root = tmp_path / "backups"

    backup_path = backup_mod_folders(sims4_dir, backup_root)

    assert backup_path.exists()
    with zipfile.ZipFile(backup_path) as archive:
        names = set(archive.namelist())
    assert "Mods/foo.package" in names
    assert "Saves/save1.save" in names


def test_backup_skips_missing_folders_without_error(tmp_path):
    sims4_dir = tmp_path / "Sims4"
    (sims4_dir / "Mods").mkdir(parents=True)
    (sims4_dir / "Mods" / "foo.package").write_bytes(b"x")
    backup_root = tmp_path / "backups"

    backup_path = backup_mod_folders(sims4_dir, backup_root)

    with zipfile.ZipFile(backup_path) as archive:
        names = set(archive.namelist())
    assert names == {"Mods/foo.package"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.backup'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/backup.py`:
```python
"""One-shot backup of Mods/Saves/Tray before the first install of a session."""
import zipfile
from datetime import datetime
from pathlib import Path

_BACKUP_FOLDERS = ("Mods", "Saves", "Tray")


def backup_mod_folders(sims4_dir: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_root / f"backup-{timestamp}.zip"

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder_name in _BACKUP_FOLDERS:
            folder_path = sims4_dir / folder_name
            if not folder_path.exists():
                continue
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(sims4_dir))

    return backup_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backup.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/backup.py tests/test_backup.py
git commit -m "feat: add Mods/Saves/Tray backup"
```

---

### Task 8: Settings toggle (Options.ini)

**Files:**
- Create: `sims_mod_manager/core/settings_toggle.py`
- Test: `tests/test_settings_toggle.py`

**Interfaces:**
- Produces: `class SettingsToggleResult(Enum)` with members `APPLIED`, `ALREADY_ENABLED`, `NEEDS_MANUAL_FALLBACK`; `enable_mods_and_script_mods(options_ini_path: Path) -> SettingsToggleResult` — used by Task 13 (GUI scaffold).

**Note on the exact keys:** community sources (EA forums, corroborated by search) document `Options.ini` using flat `key=value` lines including `scriptmodsenabled` and `modsdisabled`, enabled as `scriptmodsenabled=1` / `modsdisabled=0`. This couldn't be verified against a live file during planning (the game isn't installed in this environment). The implementation below is regex-based line rewriting that only touches lines it recognizes and never guesses a key into existence — if the expected keys aren't found, it returns `NEEDS_MANUAL_FALLBACK` instead of writing anything. Before relying on this in practice, run it once against a real post-first-launch `Options.ini` (or diff a real file's two states: checkboxes off vs. on) and adjust `_SCRIPT_MODS_KEY`/`_MODS_DISABLED_KEY` if they don't match — the fallback path means a mismatch degrades to "show the reminder," never to a corrupted file.

- [ ] **Step 1: Write the failing test**

`tests/test_settings_toggle.py`:
```python
from sims_mod_manager.core.settings_toggle import (
    SettingsToggleResult,
    enable_mods_and_script_mods,
)


def test_missing_file_needs_manual_fallback(tmp_path):
    options_ini_path = tmp_path / "Options.ini"

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.NEEDS_MANUAL_FALLBACK


def test_file_without_expected_keys_needs_manual_fallback(tmp_path):
    options_ini_path = tmp_path / "Options.ini"
    options_ini_path.write_text("somethingelse=1\n", encoding="utf-8")

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.NEEDS_MANUAL_FALLBACK
    assert options_ini_path.read_text(encoding="utf-8") == "somethingelse=1\n"


def test_already_enabled_is_left_unchanged(tmp_path):
    options_ini_path = tmp_path / "Options.ini"
    original = "scriptmodsenabled=1\nmodsdisabled=0\nothersetting=5\n"
    options_ini_path.write_text(original, encoding="utf-8")

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.ALREADY_ENABLED
    assert options_ini_path.read_text(encoding="utf-8") == original


def test_disabled_values_get_flipped_on(tmp_path):
    options_ini_path = tmp_path / "Options.ini"
    options_ini_path.write_text(
        "scriptmodsenabled=0\nmodsdisabled=1\nothersetting=5\n", encoding="utf-8"
    )

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.APPLIED
    updated = options_ini_path.read_text(encoding="utf-8")
    assert "scriptmodsenabled=1" in updated
    assert "modsdisabled=0" in updated
    assert "othersetting=5" in updated
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings_toggle.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.settings_toggle'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/settings_toggle.py`:
```python
"""Attempts to enable custom content and script mods directly in the game's
Options.ini so the player never has to open the in-game menu. Only rewrites
lines it recognizes -- if the expected keys aren't present, it reports that
a manual toggle is needed instead of guessing a key into the file."""
import re
from enum import Enum
from pathlib import Path

_SCRIPT_MODS_KEY = "scriptmodsenabled"
_MODS_DISABLED_KEY = "modsdisabled"
_KEY_LINE_PATTERN = re.compile(r"^(?P<key>\w+)\s*=\s*(?P<value>\S+)\s*$")


class SettingsToggleResult(Enum):
    APPLIED = "applied"
    ALREADY_ENABLED = "already_enabled"
    NEEDS_MANUAL_FALLBACK = "needs_manual_fallback"


def enable_mods_and_script_mods(options_ini_path: Path) -> SettingsToggleResult:
    if not options_ini_path.exists():
        return SettingsToggleResult.NEEDS_MANUAL_FALLBACK

    lines = options_ini_path.read_text(encoding="utf-8").splitlines(keepends=True)

    found_script_mods = False
    found_mods_disabled = False
    changed = False
    new_lines = []

    for line in lines:
        match = _KEY_LINE_PATTERN.match(line.strip("\r\n"))
        if match and match.group("key").lower() == _SCRIPT_MODS_KEY:
            found_script_mods = True
            if match.group("value") != "1":
                new_lines.append(f"{_SCRIPT_MODS_KEY}=1\n")
                changed = True
                continue
        elif match and match.group("key").lower() == _MODS_DISABLED_KEY:
            found_mods_disabled = True
            if match.group("value") != "0":
                new_lines.append(f"{_MODS_DISABLED_KEY}=0\n")
                changed = True
                continue
        new_lines.append(line)

    if not (found_script_mods and found_mods_disabled):
        return SettingsToggleResult.NEEDS_MANUAL_FALLBACK

    if not changed:
        return SettingsToggleResult.ALREADY_ENABLED

    options_ini_path.write_text("".join(new_lines), encoding="utf-8")
    return SettingsToggleResult.APPLIED
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_settings_toggle.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/settings_toggle.py tests/test_settings_toggle.py
git commit -m "feat: add Options.ini settings toggle with manual fallback"
```

---

### Task 9: Search launcher

**Files:**
- Create: `sims_mod_manager/core/search_launcher.py`
- Test: `tests/test_search_launcher.py`

**Interfaces:**
- Produces: `SITE_CURSEFORGE`, `SITE_MODTHESIMS`, `SITE_BOTH` (str constants), `build_curseforge_search_url(query: str) -> str`, `build_modthesims_search_url(query: str) -> str`, `open_search(query: str, site: str) -> None` — used by Task 14 (Find tab).

**Note on URLs:** `build_curseforge_search_url` was verified directly by fetching `https://www.curseforge.com/sims4/search?class=mods&search=maxis+match+hair` and confirming it returns filtered results with the query pre-filled. ModTheSims returns HTTP 403 to automated fetches and has no documented public search API, so `build_modthesims_search_url` routes through a `site:modthesims.info` web search instead of guessing at MTS's internal search endpoint — this stays correct even if MTS changes its own search URL scheme.

- [ ] **Step 1: Write the failing test**

`tests/test_search_launcher.py`:
```python
import sims_mod_manager.core.search_launcher as search_launcher
from sims_mod_manager.core.search_launcher import (
    SITE_BOTH,
    SITE_CURSEFORGE,
    SITE_MODTHESIMS,
    build_curseforge_search_url,
    build_modthesims_search_url,
    open_search,
)


def test_curseforge_url_format():
    url = build_curseforge_search_url("maxis match hair")
    assert url == "https://www.curseforge.com/sims4/search?class=mods&search=maxis+match+hair"


def test_modthesims_url_format():
    url = build_modthesims_search_url("maxis match hair")
    assert url == "https://www.google.com/search?q=site%3Amodthesims.info+maxis+match+hair"


def test_open_search_curseforge_only(monkeypatch):
    opened = []
    monkeypatch.setattr(search_launcher.webbrowser, "open", opened.append)

    open_search("hair", SITE_CURSEFORGE)

    assert opened == [build_curseforge_search_url("hair")]


def test_open_search_both_opens_two_tabs(monkeypatch):
    opened = []
    monkeypatch.setattr(search_launcher.webbrowser, "open", opened.append)

    open_search("hair", SITE_BOTH)

    assert opened == [build_curseforge_search_url("hair"), build_modthesims_search_url("hair")]


def test_open_search_unknown_site_raises():
    import pytest

    with pytest.raises(ValueError):
        open_search("hair", "not-a-real-site")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_search_launcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.search_launcher'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/search_launcher.py`:
```python
"""Opens pre-filled search-results pages in the user's default browser.
CurseForge has a documented, verified search URL. ModTheSims has no public
API and blocks automated inspection of its own search endpoint, so we route
through a site-scoped web search instead."""
import webbrowser
from urllib.parse import quote_plus

SITE_CURSEFORGE = "curseforge"
SITE_MODTHESIMS = "modthesims"
SITE_BOTH = "both"

_VALID_SITES = (SITE_CURSEFORGE, SITE_MODTHESIMS, SITE_BOTH)


def build_curseforge_search_url(query: str) -> str:
    return f"https://www.curseforge.com/sims4/search?class=mods&search={quote_plus(query)}"


def build_modthesims_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus('site:modthesims.info ' + query)}"


def open_search(query: str, site: str) -> None:
    if site not in _VALID_SITES:
        raise ValueError(f"Unknown site: {site}")

    if site in (SITE_CURSEFORGE, SITE_BOTH):
        webbrowser.open(build_curseforge_search_url(query))
    if site in (SITE_MODTHESIMS, SITE_BOTH):
        webbrowser.open(build_modthesims_search_url(query))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_search_launcher.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/search_launcher.py tests/test_search_launcher.py
git commit -m "feat: add CurseForge/ModTheSims search launcher"
```

---

### Task 10: Link router

**Files:**
- Create: `sims_mod_manager/core/link_router.py`
- Test: `tests/test_link_router.py`

**Interfaces:**
- Produces: `class LinkAction(Enum)` with members `DIRECT_DOWNLOAD`, `OPEN_IN_BROWSER`; `classify_link(url: str) -> LinkAction` — used by Task 14 (Find tab).

- [ ] **Step 1: Write the failing test**

`tests/test_link_router.py`:
```python
from sims_mod_manager.core.link_router import LinkAction, classify_link


def test_direct_zip_link_is_direct_download():
    assert classify_link("https://cdn.example.com/mods/file.zip") == LinkAction.DIRECT_DOWNLOAD


def test_direct_package_link_with_query_string_is_direct_download():
    url = "https://cdn.example.com/mods/hair.package?token=abc123"
    assert classify_link(url) == LinkAction.DIRECT_DOWNLOAD


def test_modthesims_page_link_opens_in_browser():
    url = "https://modthesims.info/d/123456/some-mod.html"
    assert classify_link(url) == LinkAction.OPEN_IN_BROWSER


def test_curseforge_project_page_link_opens_in_browser():
    url = "https://www.curseforge.com/sims4/mods/some-mod"
    assert classify_link(url) == LinkAction.OPEN_IN_BROWSER
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_link_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.link_router'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/link_router.py`:
```python
"""Classifies a pasted URL so the Find tab knows whether it can download
directly or needs to hand off to the browser."""
from enum import Enum
from urllib.parse import urlparse

DIRECT_FILE_SUFFIXES = (".zip", ".rar", ".package", ".ts4script")


class LinkAction(Enum):
    DIRECT_DOWNLOAD = "direct_download"
    OPEN_IN_BROWSER = "open_in_browser"


def classify_link(url: str) -> LinkAction:
    path = urlparse(url).path.lower()
    if path.endswith(DIRECT_FILE_SUFFIXES):
        return LinkAction.DIRECT_DOWNLOAD
    return LinkAction.OPEN_IN_BROWSER
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_link_router.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/link_router.py tests/test_link_router.py
git commit -m "feat: add pasted-link classifier"
```

---

### Task 11: Downloader

**Files:**
- Create: `sims_mod_manager/core/downloader.py`
- Test: `tests/test_downloader.py`

**Interfaces:**
- Produces: `class DownloadError(Exception)`, `download_file(url: str, dest_dir: Path) -> Path` — used by Task 14 (Find tab).

- [ ] **Step 1: Write the failing test**

`tests/test_downloader.py`:
```python
import pytest
import requests

import sims_mod_manager.core.downloader as downloader
from sims_mod_manager.core.downloader import DownloadError, download_file


class _FakeResponse:
    def __init__(self, content=b"data"):
        self._content = content

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self._content


def test_downloads_file_to_dest_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        downloader.requests, "get", lambda url, stream, timeout: _FakeResponse(b"hello world")
    )

    dest_path = download_file("https://cdn.example.com/mods/hair.zip", tmp_path)

    assert dest_path == tmp_path / "hair.zip"
    assert dest_path.read_bytes() == b"hello world"


def test_network_failure_raises_download_error(tmp_path, monkeypatch):
    def _raise(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(downloader.requests, "get", _raise)

    with pytest.raises(DownloadError):
        download_file("https://cdn.example.com/mods/hair.zip", tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_downloader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.downloader'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/downloader.py`:
```python
"""Downloads a direct-file-link mod into the staging area."""
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

_CHUNK_SIZE = 1024 * 64


class DownloadError(Exception):
    """Raised when a direct-link download fails."""


def download_file(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = unquote(Path(urlparse(url).path).name) or "downloaded_mod"
    dest_path = dest_dir / filename

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DownloadError(f"Could not download {url}: {exc}") from exc

    with dest_path.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
            handle.write(chunk)

    return dest_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_downloader.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/downloader.py tests/test_downloader.py
git commit -m "feat: add direct-link downloader"
```

---

### Task 12: Downloads watcher

**Files:**
- Create: `sims_mod_manager/core/watcher.py`
- Test: `tests/test_watcher.py`

**Interfaces:**
- Produces: `MOD_FILE_SUFFIXES` (tuple), `class DownloadsWatcher: __init__(self, downloads_dir: Path, on_new_file: Callable[[Path], None], poll_interval_seconds: float = 2.0)`, `start(self) -> None`, `stop(self) -> None` — used by Task 15 (Inbox tab).

- [ ] **Step 1: Write the failing test**

`tests/test_watcher.py`:
```python
import time

from sims_mod_manager.core.watcher import DownloadsWatcher


def test_scan_finds_only_mod_files(tmp_path):
    (tmp_path / "mod.zip").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")

    watcher = DownloadsWatcher(tmp_path, on_new_file=lambda path: None)

    assert watcher._scan() == {tmp_path / "mod.zip"}


def test_watcher_reports_new_file_exactly_once(tmp_path):
    seen = []
    watcher = DownloadsWatcher(tmp_path, on_new_file=seen.append, poll_interval_seconds=0.05)
    watcher.start()
    try:
        (tmp_path / "new_mod.package").write_bytes(b"x")
        deadline = time.time() + 2
        while time.time() < deadline and not seen:
            time.sleep(0.05)
        time.sleep(0.2)  # give one more poll cycle to prove it doesn't re-report
    finally:
        watcher.stop()

    assert seen == [tmp_path / "new_mod.package"]


def test_scan_on_missing_directory_returns_empty_set(tmp_path):
    missing_dir = tmp_path / "does_not_exist"
    watcher = DownloadsWatcher(missing_dir, on_new_file=lambda path: None)

    assert watcher._scan() == set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_watcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sims_mod_manager.core.watcher'`

- [ ] **Step 3: Write the implementation**

`sims_mod_manager/core/watcher.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_watcher.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add sims_mod_manager/core/watcher.py tests/test_watcher.py
git commit -m "feat: add Downloads folder watcher"
```

---

### Task 13: GUI scaffold (MainWindow, AppContext, InstallCoordinator)

**Files:**
- Create: `sims_mod_manager/gui/main_window.py`
- Create: `sims_mod_manager/main.py`

**Interfaces:**
- Consumes: `config.*` (Task 1), `ModStore` (Task 4), `backup_mod_folders` (Task 7), `SettingsToggleResult` + `enable_mods_and_script_mods` (Task 8), `InstallResult` + `install_mod_file` (Task 6).
- Produces: `class InstallCoordinator: __init__(self, mods_dir, staging_dir, store, sims4_dir, backup_dir)`, `install(self, source_path: Path) -> InstallResult`; `@dataclass AppContext(staging_dir: Path, downloads_dir: Path, install_coordinator: InstallCoordinator)`; `class MainWindow(QMainWindow)` — used by Task 14 (Find tab) and Task 15 (Inbox tab), which this task's `MainWindow` also wires together (so this task's manual verification happens after both tabs exist — see Step 3's note).

This task has no automated tests (GUI code, per the design spec's testing approach) — it's verified manually together with the tabs in Tasks 14 and 15.

- [ ] **Step 1: Write `main_window.py`**

`sims_mod_manager/gui/main_window.py`:
```python
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
        )

        tabs = QTabWidget()
        tabs.addTab(FindTab(context), "Find")
        tabs.addTab(InboxTab(context), "Inbox")
        self.setCentralWidget(tabs)

        self._maybe_show_settings_reminder()

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
```

Note: this imports `FindTab` from Task 14 and `InboxTab` from Task 15, which don't exist yet — that's expected. This task's code won't run standalone until those exist; the three tasks (13, 14, 15) are verified together in Task 14's manual check.

- [ ] **Step 2: Write `main.py`**

`sims_mod_manager/main.py`:
```python
"""Application entry point."""
import sys

from PySide6.QtWidgets import QApplication

from sims_mod_manager.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Commit**

```bash
git add sims_mod_manager/gui/main_window.py sims_mod_manager/main.py
git commit -m "feat: add GUI scaffold (MainWindow, AppContext, InstallCoordinator)"
```

---

### Task 14: Find tab

**Files:**
- Create: `sims_mod_manager/gui/find_tab.py`

**Interfaces:**
- Consumes: `DownloadError` + `download_file` (Task 11), `LinkAction` + `classify_link` (Task 10), `SITE_BOTH`/`SITE_CURSEFORGE`/`SITE_MODTHESIMS` + `open_search` (Task 9), `AppContext` (Task 13, for `context.staging_dir` and `context.install_coordinator`).
- Produces: `class FindTab(QWidget): __init__(self, context: AppContext)` — used by Task 13's `MainWindow`.

No automated tests (GUI code). Manually verified in Step 2 below, alongside Task 13 and Task 15.

- [ ] **Step 1: Write `find_tab.py`**

`sims_mod_manager/gui/find_tab.py`:
```python
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
```

- [ ] **Step 2: Manually verify Tasks 13-14 together**

Since Task 15's `InboxTab` doesn't exist yet, temporarily comment out the `tabs.addTab(InboxTab(context), "Inbox")` line and the `InboxTab` import in `main_window.py` to run the app standalone:

Run: `python -m sims_mod_manager.main`

Expected: a window opens titled "Sims 4 Mod Manager" with one "Find" tab. Typing a query and clicking "Search" opens browser tab(s) to CurseForge/ModTheSims with the query pre-filled. Pasting a direct `.zip`/`.package` URL and clicking "Go" downloads and installs it (verify a file appears under a real or throwaway `Mods` folder — point `config.get_mods_dir()` at a temp folder for this manual check if you don't want to touch a real install). Pasting a mod page URL (e.g. a ModTheSims download page) opens it in the browser instead.

Revert the temporary comment-out once verified.

- [ ] **Step 3: Commit**

```bash
git add sims_mod_manager/gui/find_tab.py
git commit -m "feat: add Find tab"
```

---

### Task 15: Inbox tab

**Files:**
- Create: `sims_mod_manager/gui/inbox_tab.py`
- Modify: `sims_mod_manager/gui/main_window.py` (re-enable the `InboxTab` import/usage if it was commented out for Task 14's manual check)

**Interfaces:**
- Consumes: `DownloadsWatcher` (Task 12), `AppContext` (Task 13, for `context.downloads_dir` and `context.install_coordinator`).
- Produces: `class InboxTab(QWidget): __init__(self, context: AppContext)` — used by Task 13's `MainWindow`.

No automated tests (GUI code). Manually verified in Step 2 below.

- [ ] **Step 1: Write `inbox_tab.py`**

`sims_mod_manager/gui/inbox_tab.py`:
```python
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
        result = self._context.install_coordinator.install(source_path)
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
```

- [ ] **Step 2: Confirm `main_window.py` has both tabs active**

Open `sims_mod_manager/gui/main_window.py` and confirm the `InboxTab` import and `tabs.addTab(InboxTab(context), "Inbox")` line are present and not commented out (undo the temporary change from Task 14's Step 2 if needed).

- [ ] **Step 3: Manually verify the full app**

Run: `python -m sims_mod_manager.main`

Expected: window opens with both "Find" and "Inbox" tabs. Drop a real mod `.zip` into your Downloads folder (or a test folder pointed to by `config.get_downloads_dir()` for a throwaway check) — within ~2 seconds it appears as a card in the Inbox list. Selecting it and clicking "Install selected" installs it into `Mods/<Category>/`, removes it from the list, and shows a status message. Closing the window stops the watcher thread cleanly (no hang on exit).

- [ ] **Step 4: Commit**

```bash
git add sims_mod_manager/gui/inbox_tab.py sims_mod_manager/gui/main_window.py
git commit -m "feat: add Inbox tab"
```

---

### Task 16: Packaging (single .exe)

**Files:**
- Create: `build_exe.md` (short build instructions, since this is a manual/CI step rather than app code)

No automated tests (packaging step). Manually verified in Step 2.

- [ ] **Step 1: Write build instructions and run the build**

`build_exe.md`:
```markdown
# Building the Windows executable

1. Install build dependencies: `pip install -r requirements-dev.txt`
2. From the repo root, run:
   ```
   pyinstaller --onefile --windowed --name SimsModManager sims_mod_manager/main.py
   ```
3. The output executable is at `dist/SimsModManager.exe`.

Note: `.rar` extraction depends on an `unrar`/`unar` binary being present on
the *end user's* machine, not on anything bundled into the exe. If it's
missing, `.rar` installs fail gracefully with an "extract manually" message
(see `sims_mod_manager/core/extractor.py`) rather than crashing — this is a
known, accepted limitation for v1, not a packaging bug to chase.
```

Run the build command from Step 1's instructions and confirm `dist/SimsModManager.exe` is produced without errors.

- [ ] **Step 2: Manually verify the packaged exe**

Copy `dist/SimsModManager.exe` to a folder with no Python installed (or just a folder outside the repo/venv) and double-click it.

Expected: the app window opens exactly as it did with `python -m sims_mod_manager.main` — both tabs present, search/paste-link/inbox all functional. No console window flashes (the `--windowed` flag suppresses it).

- [ ] **Step 3: Commit**

```bash
git add build_exe.md
git commit -m "docs: add packaging instructions for single-exe build"
```

(Do not commit `dist/` or `build/` — add them to `.gitignore` if not already ignored.)

- [ ] **Step 4: Add PyInstaller output dirs to `.gitignore`**

Create or append to `.gitignore`:
```
dist/
build/
*.spec
__pycache__/
*.pyc
```

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore PyInstaller build output"
```

---

### Task 17: Activity Log tab

**Files:**
- Create: `sims_mod_manager/gui/activity_tab.py`
- Modify: `sims_mod_manager/gui/main_window.py` (add `store` to `AppContext`, add a third tab)

**Interfaces:**
- Consumes: `ModStore.get_activity_log(self) -> list[dict]` (Task 4).
- Produces: `class ActivityTab(QWidget): __init__(self, context)` — used by `MainWindow`.

**Why this task exists:** the final whole-branch review found that `ModStore.get_activity_log()` was implemented and tested but never surfaced anywhere in the app — the spec's error-handling section promises install history is "recorded in-app so mistakes are traceable," but "traceable" meant "sitting in a SQLite file" with no UI. This task closes that gap with a simple read-only table.

No automated tests (GUI code, per this project's testing approach). Manually verified via an offscreen smoke test in Step 3.

- [ ] **Step 1: Add `store` to `AppContext`**

In `sims_mod_manager/gui/main_window.py`, add a `store: ModStore` field to the `AppContext` dataclass:
```python
@dataclass
class AppContext:
    staging_dir: Path
    downloads_dir: Path
    install_coordinator: InstallCoordinator
    store: ModStore
```
And pass it when constructing `context` in `MainWindow.__init__` (the `store` variable already exists there, constructed just above `install_coordinator`):
```python
context = AppContext(
    staging_dir=config.get_staging_dir(),
    downloads_dir=config.get_downloads_dir(),
    install_coordinator=install_coordinator,
    store=store,
)
```

- [ ] **Step 2: Write `activity_tab.py`**

`sims_mod_manager/gui/activity_tab.py`:
```python
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
```

- [ ] **Step 3: Wire the third tab into `MainWindow` and smoke-test**

In `main_window.py`, import `ActivityTab` and add it as a third tab:
```python
from sims_mod_manager.gui.activity_tab import ActivityTab
...
tabs.addTab(ActivityTab(context), "Activity")
```

Offscreen smoke test (no real display needed, matching Tasks 14/15's approach): construct `ActivityTab` with a fake `context` object whose `.store.get_activity_log()` returns a canned list of 2-3 dict entries (matching the shape `ModStore.get_activity_log()` actually returns), confirm the table populates with the right row count and cell values; also test with an empty list (0 rows, no crash); confirm clicking "Refresh" re-queries `get_activity_log()` (e.g. have the fake return a different list on the second call and confirm the table updates).

- [ ] **Step 4: Commit**

```bash
git add sims_mod_manager/gui/activity_tab.py sims_mod_manager/gui/main_window.py
git commit -m "feat: add read-only Activity Log tab"
```

---

### Task 18: Background install with progress feedback

**Files:**
- Modify: `sims_mod_manager/core/store.py` (allow cross-thread use)
- Create: `sims_mod_manager/gui/install_worker.py`
- Modify: `sims_mod_manager/gui/find_tab.py` (run install on the worker, show progress)
- Modify: `sims_mod_manager/gui/inbox_tab.py` (same)

**Interfaces:**
- Consumes: `InstallCoordinator.install(self, source_path: Path) -> InstallResult` (Task 13).
- Produces: `class InstallWorker(QThread)` with `succeeded = Signal(object)` (carries `InstallResult`) and `failed = Signal(str)` — used by `find_tab.py`/`inbox_tab.py`.

**Why this task exists:** installs currently run synchronously on the GUI thread inside `_on_link_submitted`/`_on_install_clicked`. For a small CC file this is instant, but larger mod packs (some Sims 4 CC bundles run into the hundreds of MB) would freeze the window with no feedback for however long extraction/copy takes — exactly the "does it look like it's hanging?" concern a non-technical user would hit. This task moves the actual install call to a background thread and shows a busy indicator while it runs, so the window stays responsive and the user can see something is happening.

No automated tests for the GUI wiring (per this project's approach), but `store.py`'s change gets a real test since it's core logic. Manually verified via an offscreen smoke test in Step 4.

- [ ] **Step 1: Write the failing test for thread-safe store access**

Add to `tests/test_store.py`:
```python
def test_store_usable_from_a_different_thread(tmp_path):
    import threading

    store = ModStore(tmp_path / "store.db")
    errors = []

    def _use_from_thread():
        try:
            store.record_install(
                source="C:/Downloads/mod.zip",
                filename="mod.package",
                category="CAS",
                file_hash="fromthread",
                installed_path="C:/Mods/CAS/mod.package",
            )
        except Exception as exc:  # sqlite3.ProgrammingError if check_same_thread wasn't disabled
            errors.append(exc)

    thread = threading.Thread(target=_use_from_thread)
    thread.start()
    thread.join(timeout=5)

    assert errors == []
    assert store.is_duplicate("fromthread") is True
    store.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store.py::test_store_usable_from_a_different_thread -v`
Expected: FAIL with `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread...`

- [ ] **Step 3: Make the store thread-safe and verify**

In `sims_mod_manager/core/store.py`, change the connection line in `ModStore.__init__`:
```python
self._conn = sqlite3.connect(db_path, check_same_thread=False)
```
This is safe here because the app only ever runs one install at a time — `find_tab.py`/`inbox_tab.py` (this task, steps below) disable their trigger controls while a worker thread is active, so there's never concurrent access from two different threads simultaneously, only sequential access from whichever single thread happens to be running at that moment.

Run: `pytest tests/test_store.py -v`
Expected: PASS, including the new test. Then run the full suite once (`pytest -v`) to confirm no regressions.

- [ ] **Step 4: Write `install_worker.py` and wire it into both tabs**

`sims_mod_manager/gui/install_worker.py`:
```python
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
```

In `find_tab.py`: add a `QProgressBar` (indeterminate: `setRange(0, 0)`), hidden by default, to the layout. In `_on_link_submitted`, after a successful `download_file(...)` call, instead of calling `self._context.install_coordinator.install(downloaded_path)` directly and wrapping it in try/except as it does now, construct an `InstallWorker(self._context.install_coordinator, downloaded_path)`, keep it on `self._worker` (required — a `QThread` with no surviving Python reference can be garbage-collected mid-run, crashing the app), disable the "Go" button, show the progress bar, connect `succeeded` to a slot that hides the progress bar, re-enables the button, and sets the status label via the existing `_describe_install_result(result)`, and connect `failed` to a slot that does the same but sets the status label to `f"Something went wrong installing this file: {message}"` (same message shape as the current except-block). Call `self._worker.start()` to kick it off. Remove the now-redundant `try/except Exception` around the install call, since `InstallWorker` catches it and reports via the `failed` signal instead.

Apply the same pattern to `inbox_tab.py`'s `_on_install_clicked`: construct the worker, disable the "Install selected" button, show a progress bar, and on `succeeded`/`failed` do the existing status-label-and-list-item-removal logic (remove the item only on the success/duplicate paths, same as today), then re-enable the button and hide the progress bar.

- [ ] **Step 5: Offscreen smoke test**

No real display needed. For `find_tab.py`: construct `FindTab` with a fake context whose `install_coordinator.install` is a plain function (not literally threaded, just callable) that either returns a canned `InstallResult`-like object or raises — since `InstallWorker` wraps whatever `install_coordinator.install` does in a real `QThread`, you can test this with a REAL `InstallWorker` and a fake `install_coordinator`, running a real `QApplication` event loop (`app.processEvents()` in a bounded polling loop, not a fixed sleep) until the `succeeded`/`failed` signal fires, and confirm: the progress bar becomes visible when the worker starts and hidden when it finishes; the button is disabled while running and re-enabled after; the status label ends up correct for both the success and the raising case. Repeat the same shape of test for `inbox_tab.py`'s install button. Do not commit this smoke-test script — run it ad hoc and describe results in your report.

- [ ] **Step 6: Commit**

```bash
git add sims_mod_manager/core/store.py tests/test_store.py sims_mod_manager/gui/install_worker.py sims_mod_manager/gui/find_tab.py sims_mod_manager/gui/inbox_tab.py
git commit -m "feat: run installs on a background thread with progress feedback"
```

---

### Task 19: Manual end-to-end verification pass

No new files — this is the spec's "Testing approach" manual pass, done once against the fully assembled app before considering it done.

- [ ] **Step 1: Real ModTheSims zip**

Search or paste-link a real mod from ModTheSims, download it manually via the opened browser tab, confirm it shows up in the Inbox within a couple seconds, and install it. Verify the resulting `.package` file(s) land under `Mods/<Category>/` at exactly one folder deep.

- [ ] **Step 2: Real CurseForge zip**

Same as Step 1, but sourced from CurseForge via the Find tab's search.

- [ ] **Step 3: `.ts4script`-only mod**

Install a script-mod-only download and confirm it's categorized as `Mods/Script/`.

- [ ] **Step 4: Deeply nested archive**

Install a mod whose zip has the `.package` file nested 3+ folders deep inside the archive, and confirm it still lands at exactly one folder deep under `Mods/` (not nested).

- [ ] **Step 5: Duplicate install**

Install the same file twice (either the same zip twice, or download the same mod again). Confirm the second attempt is reported as "already installed — skipped duplicate" and no duplicate file is written.

- [ ] **Step 6: Settings toggle**

On a machine with a real Sims 4 install where the two checkboxes are currently off, launch the app and confirm either (a) the checkboxes end up checked in-game after the app runs, or (b) the one-time reminder dialog appears — whichever `enable_mods_and_script_mods` actually resolves to given the real `Options.ini` contents on that machine. If (b), inspect the real file to correct `_SCRIPT_MODS_KEY`/`_MODS_DISABLED_KEY` in `settings_toggle.py` per the note in Task 8, then re-run this step.

- [ ] **Step 7: Backup sanity check**

After the first install of a fresh app session, confirm a `backup-<timestamp>.zip` appeared under the app data backups folder (`%LOCALAPPDATA%\SimsModManager\backups`) and contains the pre-install state of `Mods`/`Saves`/`Tray`.

Record the outcome of each step (pass/fail + notes) in the PR description or commit message when wrapping up this plan.

---

## Self-Review Notes

- **Spec coverage:** Find tab (Task 9, 10, 14) ✓; Inbox/install pipeline — extract/flatten/categorize/dedupe (Tasks 2-6) ✓; backups (Task 7) ✓; settings toggle with fallback (Task 8) ✓; error handling (extraction failures, ambiguous categorization, duplicates, missing `Options.ini`, watcher false positives, activity log — all in Tasks 4-8, 12) ✓; testing approach (unit tests for `core/*`, manual pass for GUI — Task 19) ✓; packaging as single `.exe` (Task 16) ✓; no CurseForge API / no MTS scraping (Task 9's design) ✓.
- **Placeholder scan:** no TBD/TODO markers; the one open item (`Options.ini` key names) is called out explicitly with a concrete fallback behavior and a concrete verification step (Task 8's note, Task 19 Step 6), not left vague.
- **Type consistency:** `InstallResult`, `ModStore`, `SettingsToggleResult`, `DownloadsWatcher`, `AppContext`, `InstallCoordinator` are defined once each and referenced with matching names/signatures across every consuming task.

## Addendum (post-final-review additions)

Tasks 17 and 18 were added after a final whole-branch review of Tasks 1-16 (see `.superpowers/sdd/progress.md` for the full history) found two things worth building rather than just noting: the activity log existed in the database but was never shown in the app, and installs ran synchronously on the GUI thread with no feedback for large mod packs. Two Important bugs from that same review (categorizer absolute-path leak; `get_downloads_dir()` missing the Known Folder API fix) were fixed directly against Tasks 6 and 1 respectively rather than as new tasks, since they were corrections to existing code, not new functionality — see the ledger for those commits.
