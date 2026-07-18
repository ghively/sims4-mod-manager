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
