import zipfile

import pytest

import sims_mod_manager.core.extractor as extractor
from sims_mod_manager.core.extractor import ExtractionError, extract_archive


def _make_zip(zip_path, files):
    with zipfile.ZipFile(zip_path, "w") as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)


def test_extracts_nested_zip_contents(tmp_path):
    zip_path = tmp_path / "mod.zip"
    _make_zip(zip_path, {"folder/inner/mod.package": "data"})
    dest_dir = tmp_path / "out"

    extract_archive(zip_path, dest_dir)

    assert (dest_dir / "folder" / "inner" / "mod.package").read_text() == "data"


def test_corrupt_zip_raises_extraction_error(tmp_path):
    zip_path = tmp_path / "broken.zip"
    zip_path.write_bytes(b"not a real zip file")
    dest_dir = tmp_path / "out"

    with pytest.raises(ExtractionError):
        extract_archive(zip_path, dest_dir)


def test_unsupported_suffix_raises_extraction_error(tmp_path):
    archive_path = tmp_path / "mod.7z"
    archive_path.write_bytes(b"whatever")
    dest_dir = tmp_path / "out"

    with pytest.raises(ExtractionError):
        extract_archive(archive_path, dest_dir)


def test_rar_without_backend_raises_extraction_error(tmp_path, monkeypatch):
    monkeypatch.setattr(extractor, "rarfile", None)
    archive_path = tmp_path / "mod.rar"
    archive_path.write_bytes(b"whatever")
    dest_dir = tmp_path / "out"

    with pytest.raises(ExtractionError, match="manually"):
        extract_archive(archive_path, dest_dir)
