import zipfile

from sims_mod_manager.core.installer import install_mod_file
from sims_mod_manager.core.store import ModStore


def _make_zip(zip_path, files):
    with zipfile.ZipFile(zip_path, "w") as archive:
        for relative_path, content in files.items():
            archive.writestr(relative_path, content)


def test_installs_package_from_zip(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    zip_path = downloads_dir / "hair_mod.zip"
    _make_zip(zip_path, {"HairMod/hair.package": "data"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(zip_path, mods_dir, store, staging_dir)

    assert len(result.installed) == 1
    assert result.installed[0].name == "hair.package"
    assert result.installed[0].exists()
    assert result.installed[0].parent.parent == mods_dir
    assert result.errors == []
    store.close()


def test_installing_same_zip_twice_is_flagged_as_duplicate(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    zip_path = downloads_dir / "hair_mod.zip"
    _make_zip(zip_path, {"HairMod/hair.package": "data"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    first = install_mod_file(zip_path, mods_dir, store, staging_dir)
    second = install_mod_file(zip_path, mods_dir, store, staging_dir)

    assert len(first.installed) == 1
    assert second.installed == []
    assert len(second.duplicates) == 1
    store.close()


def test_installs_direct_ts4script_file(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    script_path = downloads_dir / "gameplay.ts4script"
    script_path.write_bytes(b"script bytes")

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(script_path, mods_dir, store, staging_dir)

    assert len(result.installed) == 1
    assert result.installed[0].parent.name == "Script"
    store.close()


def test_unrecognized_file_type_produces_error(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    text_path = downloads_dir / "notes.txt"
    text_path.write_bytes(b"not a mod")

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(text_path, mods_dir, store, staging_dir)

    assert result.installed == []
    assert len(result.errors) == 1
    store.close()


def test_archive_with_no_mod_files_produces_error(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    zip_path = downloads_dir / "readme_only.zip"
    _make_zip(zip_path, {"readme.txt": "just a readme"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(zip_path, mods_dir, store, staging_dir)

    assert result.installed == []
    assert len(result.errors) == 1
    store.close()
