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
