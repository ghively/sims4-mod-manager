from pathlib import Path

from sims_mod_manager import config


def test_mods_dir_is_under_sims4_dir():
    assert config.get_mods_dir() == config.get_sims4_dir() / "Mods"


def test_saves_and_tray_dirs_are_under_sims4_dir():
    assert config.get_saves_dir() == config.get_sims4_dir() / "Saves"
    assert config.get_tray_dir() == config.get_sims4_dir() / "Tray"


def test_options_ini_path_is_under_sims4_dir():
    assert config.get_options_ini_path() == config.get_sims4_dir() / "Options.ini"


def test_sims4_dir_matches_documents_electronic_arts_layout():
    sims4_dir = config.get_sims4_dir()
    assert sims4_dir.parts[-3:] == ("Documents", "Electronic Arts", "The Sims 4")


def test_app_data_dir_is_created(tmp_path, monkeypatch):
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path)
    app_dir = config.get_app_data_dir()
    assert app_dir.exists()
    assert app_dir == tmp_path / "AppData" / "Local" / "SimsModManager"


def test_documents_dir_uses_known_folder_api_result(monkeypatch):
    monkeypatch.setattr(
        config, "_query_known_folder_path", lambda folder_id: r"D:\Redirected\Documents"
    )
    assert config.get_documents_dir() == Path(r"D:\Redirected\Documents")


def test_documents_dir_falls_back_to_home_on_known_folder_failure(tmp_path, monkeypatch):
    def _raise(folder_id):
        raise OSError("known folder lookup failed")

    monkeypatch.setattr(config, "_query_known_folder_path", _raise)
    monkeypatch.setattr(config.Path, "home", lambda: tmp_path)
    assert config.get_documents_dir() == tmp_path / "Documents"


def test_sims4_dir_composes_on_top_of_documents_dir(monkeypatch):
    monkeypatch.setattr(config, "get_documents_dir", lambda: Path(r"D:\Redirected\Documents"))
    assert config.get_sims4_dir() == Path(r"D:\Redirected\Documents") / "Electronic Arts" / "The Sims 4"
