from sims_mod_manager.core.settings_toggle import (
    SettingsToggleResult,
    enable_mods_and_script_mods,
)


def test_missing_file_needs_manual_fallback(tmp_path):
    options_ini_path = tmp_path / "Options.ini"

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.NEEDS_MANUAL_FALLBACK


def test_file_without_expected_keys_needs_manual_fallback(tmp_path):
    options_ini_path = tmp_path / "Options.ini"
    options_ini_path.write_text("somethingelse=1\n", encoding="utf-8")

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.NEEDS_MANUAL_FALLBACK
    assert options_ini_path.read_text(encoding="utf-8") == "somethingelse=1\n"


def test_already_enabled_is_left_unchanged(tmp_path):
    options_ini_path = tmp_path / "Options.ini"
    original = "scriptmodsenabled=1\nmodsdisabled=0\nothersetting=5\n"
    options_ini_path.write_text(original, encoding="utf-8")

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.ALREADY_ENABLED
    assert options_ini_path.read_text(encoding="utf-8") == original


def test_disabled_values_get_flipped_on(tmp_path):
    options_ini_path = tmp_path / "Options.ini"
    options_ini_path.write_text(
        "scriptmodsenabled=0\nmodsdisabled=1\nothersetting=5\n", encoding="utf-8"
    )

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.APPLIED
    updated = options_ini_path.read_text(encoding="utf-8")
    assert "scriptmodsenabled=1" in updated
    assert "modsdisabled=0" in updated
    assert "othersetting=5" in updated
