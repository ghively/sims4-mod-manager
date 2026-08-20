# Sims 4 Mod Manager

A Windows desktop app that automates the tedious, error-prone parts of installing custom content and mods for The Sims 4.

Installing a mod manually means: download a `.zip`/`.rar`, extract it, find the `.package`/`.ts4script` files buried somewhere inside, drop them into `Documents\Electronic Arts\The Sims 4\Mods` at no more than one folder deep (the game silently ignores anything nested deeper), avoid clobbering a file you already installed, and remember to flip two checkboxes in the game's options menu the first time. None of that is hard, but it's exactly the kind of multi-step manual process people get wrong or give up on. This app turns "I downloaded a mod" into "it's installed and categorized" with one click, and does the one-time settings toggle for you.

It does **not** scrape or auto-download from mod sites — ModTheSims and CurseForge both block that kind of automation via ToS/anti-bot measures, so the app leans on your browser for the actual download and takes over from the moment a file lands in your Downloads folder.

## What it does

The app is a single window with three tabs, all backed by one PySide6 (Qt) process:

- **Find** — a search box with a site toggle (CurseForge, ModTheSims, or both) that opens pre-filled search-results pages in your default browser. There's also a paste-a-link box: paste a direct file URL (`.zip`/`.rar`/`.package`/`.ts4script`) and the app downloads and installs it directly; paste anything else (a mod page URL) and it just opens your browser instead.
- **Inbox** — a background thread polls your Downloads folder every couple of seconds for new files matching mod patterns. Matches show up as cards; nothing is installed until you select one and click Install — the watcher only ever surfaces candidates, it never touches `Mods` on its own.
- **Activity** — a read-only log of everything that's been installed: filename, category, source, install path, timestamp.

### The install pipeline

Whether a file comes from the Inbox watcher or a pasted direct link, it goes through the same pipeline:

1. **Extract** — `.zip` via stdlib `zipfile`, `.rar` via `rarfile` (if the archive isn't a zip/rar, or `unrar`/`unar` isn't installed, the app reports a clear "extract this one manually" message instead of crashing or silently doing nothing).
2. **Flatten** — recursively find every `.package`/`.ts4script` file in the extracted tree, regardless of how deeply the archive nested them.
3. **Categorize** — sorted into `Mods/CAS`, `Mods/Build-Buy`, `Mods/Gameplay`, `Mods/Script`, or `Mods/Uncategorized`, using file extension (`.ts4script` → Script) and filename/folder keyword heuristics for the rest. Ambiguous files go to Uncategorized rather than getting a confident-looking wrong guess.
4. **Dedupe** — each file is SHA-256 hashed and checked against everything previously installed. A match is skipped and flagged as a duplicate, never silently reinstalled.
5. **Copy + record** — the file is copied into the right `Mods/<Category>` folder (with a `(2)`, `(3)`, ... suffix appended if a *different* file already has that name — collisions are never silently overwritten) and logged to a local SQLite database.

Before the first install of each app session, `Mods`, `Saves`, and `Tray` (under `Documents\Electronic Arts\The Sims 4`) are zipped into a timestamped backup, so a bad install is always recoverable.

On first launch, the app tries to locate the game's `Options.ini` and flip the "Enable Custom Content and Mods" / "Script Mods Allowed" flags directly. If the file isn't found or the expected keys aren't there, it falls back to a one-time on-screen reminder instead of guessing at the file format.

## Why it's structured the way it is

`sims_mod_manager/core/` is pure Python — no Qt imports, every function takes explicit `Path` arguments instead of reaching for real filesystem locations, so it's fully unit-testable without a display or a real Sims 4 install. `sims_mod_manager/gui/` is a thin PySide6 layer that wires widgets to `core/` functions and to a shared `AppContext`.

The one piece of real engineering worth calling out is the thread-safety. The Find and Inbox tabs each run their installs on their own background `QThread` (via `InstallWorker`/`DownloadAndInstallWorker`) so a large download or extraction doesn't freeze the GUI. That means two installs — one triggered from each tab — can genuinely run at the same moment, and they share state: one `InstallCoordinator` and one SQLite-backed `ModStore`. Two races follow directly from that:

- **The once-per-session backup flag.** `InstallCoordinator` tracks `_backed_up_this_session` as a plain bool. Without synchronization, two threads could each read it as `False` and both trigger a backup, or worse, one could start installing before the backup it depends on has actually finished.
- **Collision resolution.** `_resolve_collision()` decides a target path is free by checking `Path.exists()`, then a later step calls `shutil.copy2()` to that path — a classic check-then-act race. Two threads landing on the same "free" filename at the same instant could have one `copy2()` silently clobber the other's file, which breaks this app's explicit "never silently overwrite a file" rule.

`InstallCoordinator.install()` wraps the backup-check-and-run plus the full install call in one `threading.Lock`, so the two tabs' worker threads can run installs concurrently everywhere except this one critical section — a second install just waits its turn rather than racing. Separately, `ModStore` wraps every SQLite operation in its own lock, because the GUI thread can call into it too (e.g. the Activity tab refreshing) while an install worker thread is mid-write, which plain `sqlite3` connections don't handle safely across threads on their own.

Both of these are exercised by dedicated tests (`tests/test_install_coordinator.py`, `tests/test_store.py`) that use `threading.Barrier` to force two (or eight) threads to hit the shared state at the same instant, rather than relying on incidental timing — the kind of test that actually fails if the lock is removed.

## Running from source

Requires Windows (it resolves Documents/Downloads via the Windows Known Folder API, which accounts for OneDrive-redirected folders) and Python 3.10+.

```
pip install -r requirements-dev.txt
python -m sims_mod_manager.main
```

`requirements-dev.txt` pulls in `requirements.txt` (PySide6, `requests`, `rarfile`) plus `pytest` and `pyinstaller`. If you just want to run the app without the test/build tooling, `pip install -r requirements.txt` is enough.

`.rar` extraction additionally depends on an `unrar`/`unar` binary being present on your machine — if it's missing, `.rar` files fail extraction with an on-screen message telling you to extract manually, rather than crashing.

### Tests

```
pytest
```

67 tests across 14 files cover every module in `core/` (extraction, flattening, categorization, dedup, backup, the settings-toggle file parser, the search-URL builder, link classification, downloading) plus the threading behavior described above. There's no automated GUI testing — the `gui/` layer is thin enough that correctness lives in the `core/` logic underneath it, which is what the tests target.

### Building a standalone .exe

See [`build_exe.md`](build_exe.md) for the PyInstaller packaging steps.

## Design notes

[`docs/design.md`](docs/design.md) is the original design document written before implementation — purpose, scope, architecture, and the error-handling rules the code follows (never silently overwrite, never silently drop, always leave a manual fallback).
