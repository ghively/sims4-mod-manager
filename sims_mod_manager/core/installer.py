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


def _resolve_collision(target_path: Path) -> Path:
    """Return a path guaranteed not to already exist on disk.

    If `target_path` is free, it's returned unchanged. Otherwise this is a
    genuine filename collision between two different files (content dedupe
    already ruled out a content match), so a counter is appended before the
    suffix until an unused name is found -- never silently overwrite."""
    if not target_path.exists():
        return target_path

    counter = 2
    while True:
        candidate = target_path.with_name(
            f"{target_path.stem} ({counter}){target_path.suffix}"
        )
        if not candidate.exists():
            return candidate
        counter += 1


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
        target_path = _resolve_collision(category_dir / mod_file.name)
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
