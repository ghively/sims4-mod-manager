import zipfile
from datetime import datetime
from unittest.mock import patch, MagicMock

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


def test_backup_collision_handling_on_same_second(tmp_path):
    """Test that two backups within the same second produce different filenames."""
    sims4_dir = tmp_path / "Sims4"
    (sims4_dir / "Mods").mkdir(parents=True)
    (sims4_dir / "Mods" / "foo.package").write_bytes(b"x")
    backup_root = tmp_path / "backups"

    # Monkeypatch datetime.now to return the same timestamp both times
    fixed_time = datetime(2026, 7, 17, 17, 53, 0)

    with patch("sims_mod_manager.core.backup.datetime") as mock_datetime:
        mock_instance = MagicMock()
        mock_instance.strftime.return_value = "20260717-175300"
        mock_datetime.now.return_value = mock_instance

        backup_path1 = backup_mod_folders(sims4_dir, backup_root)
        backup_path2 = backup_mod_folders(sims4_dir, backup_root)

    # Verify both paths are different
    assert backup_path1 != backup_path2

    # Verify both files exist
    assert backup_path1.exists()
    assert backup_path2.exists()

    # Verify the naming convention (first has no counter, second has (2))
    assert backup_path1.name == "backup-20260717-175300.zip"
    assert backup_path2.name == "backup-20260717-175300 (2).zip"

    # Verify both are valid zip archives with expected content
    with zipfile.ZipFile(backup_path1) as archive1:
        names1 = set(archive1.namelist())
    assert "Mods/foo.package" in names1

    with zipfile.ZipFile(backup_path2) as archive2:
        names2 = set(archive2.namelist())
    assert "Mods/foo.package" in names2
