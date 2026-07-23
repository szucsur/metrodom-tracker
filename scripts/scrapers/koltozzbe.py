"""Scraper for koltozzbe.hu — a Hungarian real-estate listing aggregator.

Verified working: the per-district list page
(https://koltozzbe.hu/kiado-lakas-alberlet-budapest-{district}-kerulet) is
plain server-rendered HTML, one <div class="listing-card"> per listing,
with clean structured fields — a stable "data-lid" listing ID, a
"listing-rooms"/"listing-size" pair with room count and floor area, and
an "item-type"/"item-price" pair with price and address — no browser
needed, and no free-text regex parsing required for size/rooms the way
maxapro.py needs (this source exposes them as dedicated fields).

Room count sometimes uses Hungarian "N + M szoba" notation (e.g. "2 + 1
szoba" for two full rooms plus one half-room) instead of a single number;
all digit groups in that field are summed to get a total room count,
consistent with how a person reads that notation as N+M total rooms.
"""

import re
from typing import List

import requests
from bs4 import BeautifulSoup

import config
from models import Listing

BASE_URL = "https://koltozzbe.hu"
SEARCH_URL = f"{BASE_URL}/kiado-lakas-alberlet-budapest-{config.ALBERLET_DISTRICT_CODE}-kerulet"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

_SIZE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m")
_DIGITS_RE = re.compile(r"\d+")


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[koltozzbe.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for card in soup.find_all("div", class_="listing-card"):
        listing_id = card.get("data-lid")
        link = card.find("a", class_="listing-item-link", href=True)
        if not listing_id or not link:
            continue
        href = link["href"]
        url = href if href.startswith("http") else f"{BASE_URL}{href}"
        title = link.get("title", "").strip()

        price_el = card.find("div", class_="item-type")
        price_text = ""
        if price_el:
            first_text = price_el.find(string=True, recursive=False)
            price_text = first_text.strip() if first_text else ""

        address_el = card.find("div", class_="item-price")
        address_text = address_el.get_text(strip=True) if address_el else ""

        desc_el = card.find("p")
        description_text = desc_el.get_text(strip=True) if desc_el else ""

        size_el = card.find("div", class_="listing-size")
        size_match = _SIZE_RE.search(size_el.get_text()) if size_el else None
        size_sqm = float(size_match.group(1).replace(",", ".")) if size_match else None

        rooms_el = card.find("div", class_="listing-rooms")
        rooms = None
        if rooms_el:
            digit_groups = _DIGITS_RE.findall(rooms_el.get_text())
            if digit_groups:
                rooms = float(sum(int(d) for d in digit_groups))

        listings.append(Listing(
            source="koltozzbe.hu",
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
