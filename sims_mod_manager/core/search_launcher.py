"""Opens pre-filled search-results pages in the user's default browser.
CurseForge has a documented, verified search URL. ModTheSims has no public
API and blocks automated inspection of its own search endpoint, so we route
through a site-scoped web search instead."""
import webbrowser
from urllib.parse import quote_plus

SITE_CURSEFORGE = "curseforge"
SITE_MODTHESIMS = "modthesims"
SITE_BOTH = "both"

_VALID_SITES = (SITE_CURSEFORGE, SITE_MODTHESIMS, SITE_BOTH)


def build_curseforge_search_url(query: str) -> str:
    return f"https://www.curseforge.com/sims4/search?class=mods&search={quote_plus(query)}"


def build_modthesims_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus('site:modthesims.info ' + query)}"


def open_search(query: str, site: str) -> None:
    if site not in _VALID_SITES:
        raise ValueError(f"Unknown site: {site}")

    if site in (SITE_CURSEFORGE, SITE_BOTH):
        webbrowser.open(build_curseforge_search_url(query))
    if site in (SITE_MODTHESIMS, SITE_BOTH):
        webbrowser.open(build_modthesims_search_url(query))
