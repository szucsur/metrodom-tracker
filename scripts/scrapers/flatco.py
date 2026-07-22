"""Scraper for flatco.hu — Metrodom's own property management site.

flatco.hu is not a generic listing portal; it's run by Metrodom (the
building's own management company), and its global nav exposes every
currently-available rental unit directly as a link with text like
"Metrodom Green - A.B.304" -> /rental/metrodom-green-a-b-304/. That nav
is present on every page (confirmed on the homepage), so this is
effectively the landlord's own live "available now" list — simpler and
more authoritative than any generic search, and no filtering by
district/price/etc. is needed since the link list already only contains
genuinely available units.

This scraper fetches the homepage, finds nav links whose "Building -
Unit" text matches config.ADDRESS_KEYWORDS, and follows each into its
detail page to pull price/size/rooms/furnished/terrace/description.
"""

import re
from typing import List

import requests
from bs4 import BeautifulSoup

import config
from models import Listing

HOME_URL = "https://flatco.hu/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

_UNIT_LINK_RE = re.compile(r"^(.+?)\s+-\s+([\w.]+)$")


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(HOME_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[flatco.hu] request failed: {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    unit_links = _find_matching_unit_links(soup)

    listings = []
    for building, unit_code, href in unit_links:
        detail = _fetch_detail(session, href)
        if detail:
            listings.append(detail)
    return listings


def _find_matching_unit_links(soup: BeautifulSoup):
    """Nav links like 'Metrodom Green - A.B.304' whose building name
    matches config.FLATCO_BUILDING_NAME exactly (not the looser, more
    generic config.ADDRESS_KEYWORDS — flatco.hu manages several other
    Metrodom buildings, and "metrodom" alone would match those too)."""
    matches = []
    seen_hrefs = set()
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        m = _UNIT_LINK_RE.match(text)
        if not m:
            continue
        building, unit_code = m.groups()
        if a["href"] in seen_hrefs:
            continue
        if building.lower() == config.FLATCO_BUILDING_NAME:
            seen_hrefs.add(a["href"])
            matches.append((building, unit_code, a["href"]))
    return matches


def _fetch_detail(session: requests.Session, url: str) -> Listing:
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[flatco.hu] detail request failed for {url}: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    body = soup.find("body")
    text = re.sub(r"\s+", " ", body.get_text(" ", strip=True)) if body else ""

    price_match = re.search(r"([\d\s]{3,})\s*HUF\s*/\s*h[oó]nap", text, re.IGNORECASE)
    price_text = f"{price_match.group(1).strip()} HUF/hónap" if price_match else ""

    size_match = re.search(r"(\d+)\s*m²", text)
    size_sqm = float(size_match.group(1)) if size_match else None

    rooms_match = re.search(r"(\d+)\s*szoba", text, re.IGNORECASE)
    rooms = float(rooms_match.group(1)) if rooms_match else None

    listing_id = url.rstrip("/").rsplit("/", 1)[-1]
    title_match = re.search(r"(Metrodom [\w.]+ - [\w.]+)", text)
    title = title_match.group(1) if title_match else listing_id

    return Listing(
        source="flatco.hu",
        listing_id=listing_id,
        url=url,
        title=title,
        price_text=price_text,
        size_sqm=size_sqm,
        rooms=rooms,
        address_text=title,
        description_text=text,
    )
