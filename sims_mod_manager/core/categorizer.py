"""Assigns a Sims 4 mod file to one of a fixed set of category folders."""
from pathlib import Path

CATEGORY_CAS = "CAS"
CATEGORY_BUILD_BUY = "Build-Buy"
CATEGORY_GAMEPLAY = "Gameplay"
CATEGORY_SCRIPT = "Script"
CATEGORY_UNCATEGORIZED = "Uncategorized"

ALL_CATEGORIES = (
    CATEGORY_CAS,
    CATEGORY_BUILD_BUY,
    CATEGORY_GAMEPLAY,
    CATEGORY_SCRIPT,
    CATEGORY_UNCATEGORIZED,
)

_CAS_KEYWORDS = (
    "hair", "skin", "eye", "eyes", "makeup", "cas", "clothing", "outfit",
    "accessor", "tattoo", "eyebrow", "eyelash",
)
_BUILD_BUY_KEYWORDS = (
    "build", "buy", "furniture", "object", "wallpaper", "floor", "deco",
    "curtain", "rug", "lighting",
)
_GAMEPLAY_KEYWORDS = (
    "gameplay", "trait", "career", "overhaul", "tuning", "interaction",
)


def categorize_file(file_path: Path) -> str:
    if file_path.suffix.lower() == ".ts4script":
        return CATEGORY_SCRIPT

    haystack = " ".join(part.lower() for part in (file_path.stem, *file_path.parts))

    if any(keyword in haystack for keyword in _CAS_KEYWORDS):
        return CATEGORY_CAS
    if any(keyword in haystack for keyword in _BUILD_BUY_KEYWORDS):
        return CATEGORY_BUILD_BUY
    if any(keyword in haystack for keyword in _GAMEPLAY_KEYWORDS):
        return CATEGORY_GAMEPLAY

    return CATEGORY_UNCATEGORIZED
