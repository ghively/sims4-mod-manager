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

    if suffix not in (".zip", ".rar"):
        raise ExtractionError(f"Unsupported archive format: {suffix}")

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExtractionError(
            f"Could not prepare a folder to extract {archive_path.name} into: {exc}"
        ) from exc

    if suffix == ".zip":
        _extract_zip(archive_path, dest_dir)
    else:
        _extract_rar(archive_path, dest_dir)


def _extract_zip(archive_path: Path, dest_dir: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(dest_dir)
    except zipfile.BadZipFile as exc:
        raise ExtractionError(
            f"Could not open {archive_path.name}: not a valid zip file"
        ) from exc
    except OSError as exc:
        raise ExtractionError(
            f"Could not extract {archive_path.name}: {exc}"
        ) from exc


_RAR_MANUAL_EXTRACT_HINT = (
    "Please extract it manually and drop the contents into the Inbox."
)


def _extract_rar(archive_path: Path, dest_dir: Path) -> None:
    if rarfile is None:
        raise ExtractionError(
            f"Could not open {archive_path.name}: RAR extraction isn't available on "
            f"this machine. {_RAR_MANUAL_EXTRACT_HINT}"
        )
    try:
        with rarfile.RarFile(archive_path) as archive:
            archive.extractall(dest_dir)
    except (rarfile.Error, OSError) as exc:
        raise ExtractionError(
            f"Could not open {archive_path.name}: {exc} {_RAR_MANUAL_EXTRACT_HINT}"
        ) from exc
