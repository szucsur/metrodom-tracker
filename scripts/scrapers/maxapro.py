"""Scraper for maxapro.hu — a general Hungarian classifieds site with a
real-estate rental section.

Verified working: the per-district list page
(https://maxapro.hu/budapest-{district}-kerulet/kiado-haz-lakas) is plain
server-rendered HTML, one <li class="srBlock"> card per listing — no
browser needed. Unlike alberlet.hu/megveszlak.hu, the list page doesn't
expose size/room count as separate fields — they only ever appear inside
the free-text ad description (and are often truncated there) — so they're
extracted via regex from that text, the same best-effort approach already
used elsewhere in this project (e.g. filters.parse_price_huf() on price
text); an unparseable size/room count fails the hard filter exactly like
an unparseable price already does, not a new behavior.
"""

import re
from typing import List

import requests
from bs4 import BeautifulSoup

import config
from models import Listing

BASE_URL = "https://maxapro.hu"
SEARCH_URL = f"{BASE_URL}/budapest-{config.ALBERLET_DISTRICT_CODE}-kerulet/kiado-haz-lakas"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

_ID_RE = re.compile(r"-(\d+)$")
_SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m²")
_ROOMS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*szob")


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[maxapro.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for card in soup.find_all("li", class_="srBlock"):
        heading = card.find("h3")
        link = heading.find("a", href=True) if heading else None
        if not link:
            continue
        href = link["href"]
        match = _ID_RE.search(href)
        if not match:
            continue
        listing_id = match.group(1)
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        title = link.get_text(strip=True)

        location_el = card.find("div", class_="location")
        address_text = location_el.get_text(strip=True) if location_el else ""

        desc_el = card.find("div", class_="srDesc")
        description_text = desc_el.get_text(strip=True) if desc_el else ""

        price_el = card.find("div", class_="srPrice")
        price_text = price_el.get_text(strip=True) if price_el else ""

        size_match = _SIZE_RE.search(description_text)
        size_sqm = float(size_match.group(1).replace(",", ".")) if size_match else None

        rooms_match = _ROOMS_RE.search(description_text)
        rooms = float(rooms_match.group(1).replace(",", ".")) if rooms_match else None

        listings.append(Listing(
            source="maxapro.hu",
            listing_id=listing_id,
            url=url,
            title=title,
            price_text=price_text,
            size_sqm=size_sqm,
            rooms=rooms,
            address_text=address_text,
            description_text=f"{title} {address_text} {description_text}",
        ))

    return listings
