from sims_mod_manager.core.flattener import find_mod_files


def test_finds_mod_files_at_any_depth(tmp_path):
    (tmp_path / "top.package").write_bytes(b"x")
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (nested / "deep.ts4script").write_bytes(b"x")

    found = find_mod_files(tmp_path)

    assert found == sorted([tmp_path / "top.package", nested / "deep.ts4script"])


def test_ignores_non_mod_files(tmp_path):
    (tmp_path / "readme.txt").write_bytes(b"x")
    (tmp_path / "preview.jpg").write_bytes(b"x")

    assert find_mod_files(tmp_path) == []


def test_empty_directory_returns_empty_list(tmp_path):
    assert find_mod_files(tmp_path) == []
