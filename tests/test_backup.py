import zipfile

from sims_mod_manager.core.backup import backup_mod_folders


def test_backup_includes_mods_and_saves_files(tmp_path):
    sims4_dir = tmp_path / "Sims4"
    (sims4_dir / "Mods").mkdir(parents=True)
    (sims4_dir / "Mods" / "foo.package").write_bytes(b"x")
    (sims4_dir / "Saves").mkdir(parents=True)
    (sims4_dir / "Saves" / "save1.save").write_bytes(b"x")
    backup_root = tmp_path / "backups"

    backup_path = backup_mod_folders(sims4_dir, backup_root)

    assert backup_path.exists()
    with zipfile.ZipFile(backup_path) as archive:
        names = set(archive.namelist())
    assert "Mods/foo.package" in names
    assert "Saves/save1.save" in names


def test_backup_skips_missing_folders_without_error(tmp_path):
    sims4_dir = tmp_path / "Sims4"
    (sims4_dir / "Mods").mkdir(parents=True)
    (sims4_dir / "Mods" / "foo.package").write_bytes(b"x")
    backup_root = tmp_path / "backups"

    backup_path = backup_mod_folders(sims4_dir, backup_root)

    with zipfile.ZipFile(backup_path) as archive:
        names = set(archive.namelist())
    assert names == {"Mods/foo.package"}
