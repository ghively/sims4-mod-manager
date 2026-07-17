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
