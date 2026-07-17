from pathlib import Path

from sims_mod_manager.core.categorizer import (
    CATEGORY_BUILD_BUY,
    CATEGORY_CAS,
    CATEGORY_GAMEPLAY,
    CATEGORY_SCRIPT,
    CATEGORY_UNCATEGORIZED,
    categorize_file,
)


def test_ts4script_is_always_script_category():
    assert categorize_file(Path("SomeMod/whatever.ts4script")) == CATEGORY_SCRIPT


def test_hair_package_is_cas():
    assert categorize_file(Path("MaxisMatch_ToddlerHair.package")) == CATEGORY_CAS


def test_furniture_package_is_build_buy():
    assert categorize_file(Path("ModernFurniture_Set.package")) == CATEGORY_BUILD_BUY


def test_trait_package_is_gameplay():
    assert categorize_file(Path("NewTrait_Overhaul.package")) == CATEGORY_GAMEPLAY


def test_unrecognized_package_is_uncategorized():
    assert categorize_file(Path("xyz123.package")) == CATEGORY_UNCATEGORIZED


def test_keyword_match_in_parent_folder_name_counts():
    assert categorize_file(Path("Downloads/Hair Pack/file01.package")) == CATEGORY_CAS
