import sims_mod_manager.core.search_launcher as search_launcher
from sims_mod_manager.core.search_launcher import (
    SITE_BOTH,
    SITE_CURSEFORGE,
    SITE_MODTHESIMS,
    build_curseforge_search_url,
    build_modthesims_search_url,
    open_search,
)


def test_curseforge_url_format():
    url = build_curseforge_search_url("maxis match hair")
    assert url == "https://www.curseforge.com/sims4/search?class=mods&search=maxis+match+hair"


def test_modthesims_url_format():
    url = build_modthesims_search_url("maxis match hair")
    assert url == "https://www.google.com/search?q=site%3Amodthesims.info+maxis+match+hair"


def test_open_search_curseforge_only(monkeypatch):
    opened = []
    monkeypatch.setattr(search_launcher.webbrowser, "open", opened.append)

    open_search("hair", SITE_CURSEFORGE)

    assert opened == [build_curseforge_search_url("hair")]


def test_open_search_both_opens_two_tabs(monkeypatch):
    opened = []
    monkeypatch.setattr(search_launcher.webbrowser, "open", opened.append)

    open_search("hair", SITE_BOTH)

    assert opened == [build_curseforge_search_url("hair"), build_modthesims_search_url("hair")]


def test_open_search_unknown_site_raises():
    import pytest

    with pytest.raises(ValueError):
        open_search("hair", "not-a-real-site")
