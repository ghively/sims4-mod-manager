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
