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
