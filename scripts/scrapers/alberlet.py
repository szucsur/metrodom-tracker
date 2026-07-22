"""Scraper for alberlet.hu search results.

The search-results page is server-rendered (confirmed: a plain GET
returns full listing content, no JS/browser needed). The search URL is
built directly from query params matching the site's own search form:

    https://www.alberlet.hu/kiado-alberlet
        ?ingatlan-tipus=lakas
        &kerulet={district}          e.g. "ix" for Budapest IX. kerület
        &meret={min_size}-x-m2       e.g. "40-x-m2" for 40+ sqm
        &szoba={min_rooms}-x         e.g. "2-x" for 2+ rooms
        &keres=normal&limit=24

Each listing's detail-page URL is a self-describing slug, e.g.
/kiado-alberlet/budapest-IX-kerulet-vagohid-utca-65m2-3-szoba_779416
which conveniently encodes district, street, size, room count, and a
unique numeric ID — parsed directly instead of relying on card markup,
since that's more stable across redesigns than CSS class names.
"""

import re
from typing import List

import requests
from bs4 import BeautifulSoup

import config
from models import Listing

SEARCH_URL = "https://www.alberlet.hu/kiado-alberlet"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

_SLUG_RE = re.compile(
    r"/kiado-alberlet/budapest-([a-zA-Z]+)-kerulet-(.+?)-(\d+)m2-(\d+)-szoba_(\d+)$"
)


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    params = {
        "ingatlan-tipus": "lakas",
        "kerulet": config.ALBERLET_DISTRICT_CODE,
        "meret": f"{config.MIN_SIZE_SQM}-x-m2",
        "szoba": f"{config.MIN_ROOMS}-x",
        "keres": "normal",
        "limit": "24",
    }
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[alberlet.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = {}  # listing_id -> Listing, since each href appears twice per card

    for a in soup.find_all("a", href=True):
        match = _SLUG_RE.search(a["href"])
        if not match:
            continue
        district, street_slug, size_str, rooms_str, listing_id = match.groups()

        price_span = a.find("span", class_="price")
        price_text = f"{price_span.get_text(strip=True)} Ft/hó" if price_span else ""

        existing = listings.get(listing_id)
        if existing and (price_text == "" or existing.price_text):
            continue  # already recorded, and this occurrence adds nothing new

        street = street_slug.replace("-", " ")
        address_text = f"{street} Budapest, {district}. kerület"

        listings[listing_id] = Listing(
            source="alberlet.hu",
            listing_id=listing_id,
            url=f"https://www.alberlet.hu{a['href']}",
            title=f"{street} - {size_str} m2, {rooms_str} szoba",
            price_text=price_text,
            size_sqm=float(size_str),
            rooms=float(rooms_str),
            address_text=address_text,
            description_text=address_text,
        )

    return list(listings.values())
