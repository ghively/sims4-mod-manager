"""Attempts to enable custom content and script mods directly in the game's
Options.ini so the player never has to open the in-game menu. Only rewrites
lines it recognizes -- if the expected keys aren't present, it reports that
a manual toggle is needed instead of guessing a key into the file."""
import re
from enum import Enum
from pathlib import Path

_SCRIPT_MODS_KEY = "scriptmodsenabled"
_MODS_DISABLED_KEY = "modsdisabled"
_KEY_LINE_PATTERN = re.compile(r"^(?P<key>\w+)\s*=\s*(?P<value>\S+)\s*$")


class SettingsToggleResult(Enum):
    APPLIED = "applied"
    ALREADY_ENABLED = "already_enabled"
    NEEDS_MANUAL_FALLBACK = "needs_manual_fallback"


def enable_mods_and_script_mods(options_ini_path: Path) -> SettingsToggleResult:
    if not options_ini_path.exists():
        return SettingsToggleResult.NEEDS_MANUAL_FALLBACK

    lines = options_ini_path.read_text(encoding="utf-8").splitlines(keepends=True)

    found_script_mods = False
    found_mods_disabled = False
    changed = False
    new_lines = []

    for line in lines:
        stripped = line.strip("\r\n")
        terminator = line[len(stripped):]
        match = _KEY_LINE_PATTERN.match(stripped)
        if match and match.group("key").lower() == _SCRIPT_MODS_KEY:
            found_script_mods = True
            if match.group("value") != "1":
                new_lines.append(f"{_SCRIPT_MODS_KEY}=1{terminator}")
                changed = True
                continue
        elif match and match.group("key").lower() == _MODS_DISABLED_KEY:
            found_mods_disabled = True
            if match.group("value") != "0":
                new_lines.append(f"{_MODS_DISABLED_KEY}=0{terminator}")
                changed = True
                continue
        new_lines.append(line)

    if not (found_script_mods and found_mods_disabled):
        return SettingsToggleResult.NEEDS_MANUAL_FALLBACK

    if not changed:
        return SettingsToggleResult.ALREADY_ENABLED

    options_ini_path.write_text("".join(new_lines), encoding="utf-8")
    return SettingsToggleResult.APPLIED
