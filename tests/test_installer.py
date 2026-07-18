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


def test_filename_collision_between_different_files_is_disambiguated_not_overwritten(tmp_path):
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()

    first_zip = downloads_dir / "hair_a.zip"
    _make_zip(first_zip, {"HairModA/somefile.package": "content a"})

    second_zip = downloads_dir / "hair_b.zip"
    _make_zip(second_zip, {"HairModB/somefile.package": "content b"})

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    first = install_mod_file(first_zip, mods_dir, store, staging_dir)
    second = install_mod_file(second_zip, mods_dir, store, staging_dir)

    assert len(first.installed) == 1
    original_path = first.installed[0]
    assert original_path.name == "somefile.package"
    assert original_path.parent == mods_dir / "CAS"

    assert len(second.installed) == 1
    disambiguated_path = second.installed[0]
    assert disambiguated_path.name == "somefile (2).package"
    assert disambiguated_path.parent == mods_dir / "CAS"

    assert first.duplicates == []
    assert second.duplicates == []

    assert original_path.exists()
    assert disambiguated_path.exists()
    assert original_path.read_bytes() == b"content a"
    assert disambiguated_path.read_bytes() == b"content b"

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


def test_categorization_ignores_staging_dir_absolute_path_for_archives(tmp_path):
    # Regression test: categorize_file() matches on substrings, so an
    # absolute staging path containing a keyword-colliding folder name (e.g.
    # a Windows username like "Cassidy" or a system folder like this one,
    # "castle_user", both contain "cas") must NOT leak into categorization.
    # Only the archive's own internal folder structure and filename should
    # be considered. The file itself ("SomeFolder/plain.package") has no
    # CAS/Build-Buy/Gameplay keywords, so it should end up Uncategorized --
    # not CAS, which is what the bug would produce.
    downloads_dir = tmp_path / "downloads"
    downloads_dir.mkdir()
    zip_path = downloads_dir / "plain_mod.zip"
    _make_zip(zip_path, {"SomeFolder/plain.package": "data"})

    mods_dir = tmp_path / "Mods"
    # Deliberately keyword-colliding staging path: "castle_user" contains "cas".
    staging_dir = tmp_path / "castle_user" / "downloads"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(zip_path, mods_dir, store, staging_dir)

    assert len(result.installed) == 1
    assert result.installed[0].name == "plain.package"
    assert result.installed[0].parent.name == "Uncategorized"
    assert result.installed[0].exists()
    assert result.errors == []
    store.close()


def test_categorization_ignores_containing_folder_for_direct_files(tmp_path):
    # Same regression, but for a direct (non-archive) mod file dropped
    # straight into a folder whose absolute path collides with a keyword
    # (again "cas" via "castle_user"). Only the filename itself should be
    # used for categorization, so a keyword-free filename must be
    # Uncategorized rather than CAS.
    downloads_dir = tmp_path / "castle_user" / "downloads"
    downloads_dir.mkdir(parents=True)
    package_path = downloads_dir / "plain.package"
    package_path.write_bytes(b"data")

    mods_dir = tmp_path / "Mods"
    staging_dir = tmp_path / "staging"
    store = ModStore(tmp_path / "store.db")

    result = install_mod_file(package_path, mods_dir, store, staging_dir)

    assert len(result.installed) == 1
    assert result.installed[0].name == "plain.package"
    assert result.installed[0].parent.name == "Uncategorized"
    assert result.installed[0].exists()
    assert result.errors == []
    store.close()
