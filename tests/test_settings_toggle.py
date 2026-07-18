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


def test_preserves_crlf_line_endings(tmp_path):
    """Verify that rewritten lines preserve the original CRLF line endings.

    Writes the input with newline="" so the on-disk bytes are unambiguously
    \\r\\n regardless of platform, and reads the output back with read_bytes()
    so the assertion sidesteps any text-mode newline translation entirely.
    This makes the test genuinely platform-independent: it would fail if the
    line-ending preservation logic regressed, unlike a text-mode round trip
    which can be silently "fixed" by the OS's own newline coercion.
    """
    options_ini_path = tmp_path / "Options.ini"
    original_content = "scriptmodsenabled=0\r\nmodsdisabled=1\r\nothersetting=5\r\n"
    options_ini_path.write_text(original_content, encoding="utf-8", newline="")

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.APPLIED
    output_bytes = options_ini_path.read_bytes()
    assert output_bytes == (
        b"scriptmodsenabled=1\r\nmodsdisabled=0\r\nothersetting=5\r\n"
    )


def test_preserves_lf_only_line_endings(tmp_path):
    """Verify that LF-only files are not force-converted to CRLF.

    This is the mirror-image bug: a naive fix could preserve CRLF but always
    emit CRLF regardless of what the original file used. Writing with
    newline="" and asserting on read_bytes() proves the output stays
    byte-for-byte LF-only.
    """
    options_ini_path = tmp_path / "Options.ini"
    original_content = "scriptmodsenabled=0\nmodsdisabled=1\nothersetting=5\n"
    options_ini_path.write_text(original_content, encoding="utf-8", newline="")

    result = enable_mods_and_script_mods(options_ini_path)

    assert result == SettingsToggleResult.APPLIED
    output_bytes = options_ini_path.read_bytes()
    assert output_bytes == (
        b"scriptmodsenabled=1\nmodsdisabled=0\nothersetting=5\n"
    )
