from sims_mod_manager.core.link_router import LinkAction, classify_link


def test_direct_zip_link_is_direct_download():
    assert classify_link("https://cdn.example.com/mods/file.zip") == LinkAction.DIRECT_DOWNLOAD


def test_direct_package_link_with_query_string_is_direct_download():
    url = "https://cdn.example.com/mods/hair.package?token=abc123"
    assert classify_link(url) == LinkAction.DIRECT_DOWNLOAD


def test_modthesims_page_link_opens_in_browser():
    url = "https://modthesims.info/d/123456/some-mod.html"
    assert classify_link(url) == LinkAction.OPEN_IN_BROWSER


def test_curseforge_project_page_link_opens_in_browser():
    url = "https://www.curseforge.com/sims4/mods/some-mod"
    assert classify_link(url) == LinkAction.OPEN_IN_BROWSER
