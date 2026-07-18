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
