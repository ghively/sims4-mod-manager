"""One-shot backup of Mods/Saves/Tray before the first install of a session."""
import zipfile
from datetime import datetime
from pathlib import Path

_BACKUP_FOLDERS = ("Mods", "Saves", "Tray")


def backup_mod_folders(sims4_dir: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_root / f"backup-{timestamp}.zip"

    # Handle collision: if file exists, append incrementing counter
    counter = 2
    while backup_path.exists():
        backup_path = backup_root / f"backup-{timestamp} ({counter}).zip"
        counter += 1

    with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for folder_name in _BACKUP_FOLDERS:
            folder_path = sims4_dir / folder_name
            if not folder_path.exists():
                continue
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(sims4_dir))

    return backup_path
