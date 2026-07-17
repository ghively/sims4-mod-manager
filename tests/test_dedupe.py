import hashlib

from sims_mod_manager.core.dedupe import hash_file


def test_hash_matches_direct_sha256(tmp_path):
    file_path = tmp_path / "sample.package"
    file_path.write_bytes(b"hello world")

    assert hash_file(file_path) == hashlib.sha256(b"hello world").hexdigest()


def test_different_content_gives_different_hash(tmp_path):
    file_a = tmp_path / "a.package"
    file_b = tmp_path / "b.package"
    file_a.write_bytes(b"content a")
    file_b.write_bytes(b"content b")

    assert hash_file(file_a) != hash_file(file_b)
