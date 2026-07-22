"""Scraper for megveszlak.hu — a large nationwide listing aggregator
(160k+ listings site-wide).

Important limitation, confirmed by inspecting both the district rental
list page and an individual listing's detail page: megveszlak.hu only
ever exposes district/neighborhood-level location (e.g. "Albérlet (lakás)
Budapest V. kerület, Belváros") — no street name anywhere, not even on the
detail page (no JSON-LD, no lat/lng, no address field beyond the district
name). Same limitation as albifigyelo.hu, so this is wired up the same
way: Listing.location_precision = "district", which filters.py accepts
against LOCATION_HINTS alone (no street-name match required) and flags
with a "verify manually" note.

The site provides a per-district list URL directly
(https://megveszlak.hu/alberlet-budapest-ix-kerulet), which is used here
via config.ALBERLET_DISTRICT_CODE (the same district code already used by
alberlet.hu) instead of paging through the citywide list — the source
only ever supports district-level matching anyway, so there is nothing
lost by pre-filtering server-side to the right district.
"""

import re
from typing import List

import requests
from bs4 import BeautifulSoup

import config
from models import Listing

BASE_URL = "https://megveszlak.hu"
SEARCH_URL = f"{BASE_URL}/alberlet-budapest-{config.ALBERLET_DISTRICT_CODE}-kerulet"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

_ID_RE = re.compile(r"-(\d+)$")


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[megveszlak.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for container in soup.find_all("div", class_="hirdetes_lista_hirdetes_container"):
        link = container.find("a", href=re.compile(r"^/hirdetes/"))
        if not link:
            continue
        href = link["href"]
        match = _ID_RE.search(href)
        if not match:
            continue
        listing_id = match.group(1)

        price_el = container.find("div", class_="hirdetes_item_ar")
        price_text = price_el.get_text(strip=True) if price_el else ""

        cim_el = container.find("div", class_="hirdetes_item_cim")
        address_text = cim_el.get_text(strip=True) if cim_el else ""

        size_sqm = rooms = None
        for div in container.find_all("div", class_="hirdetes_item_meretekdiv"):
            label = div.find("span")
            label_text = label.get_text(strip=True) if label else ""
            spans = div.find_all("span")
            value_text = spans[1].get_text(strip=True) if len(spans) > 1 else ""
            if label_text.startswith("Alapterület"):
                m = re.search(r"(\d+(?:[.,]\d+)?)", value_text)
                if m:
                    size_sqm = float(m.group(1).replace(",", "."))
            elif label_text.startswith("Szobaszám"):
                m = re.search(r"(\d+(?:[.,]\d+)?)", value_text)
                if m:
                    rooms = float(m.group(1).replace(",", "."))

        title = link.get("title") or address_text

        listings.append(Listing(
            source="megveszlak.hu",
            listing_id=listing_id,
            url=f"{BASE_URL}{href}",
            title=title,
            price_text=price_text,
            size_sqm=size_sqm,
            rooms=rooms,
            address_text=address_text,
            description_text=f"{title} {address_text}",
            location_precision="district",
        ))

    return listings
