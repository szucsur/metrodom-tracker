"""Scraper for tappancsosotthon.hu ("Rent with Paws") — a small
pet-friendly rental agency in Budapest.

Despite the Hungarian name ("Tappancsos Otthon" = "Pawed Home") reading
like it could be an animal shelter, this is a genuine rental listing
site: a boutique agency specializing in pet-friendly apartment rentals,
built on WordPress with the "Essential Real Estate" plugin.

The homepage renders every published listing directly — confirmed no
pagination links exist and the page already contains ~400 unique
/property/{slug}/ URLs in one GET — and each card already carries price,
size, room count, and (unlike several other sources here) the actual
street name right in the listing title itself (e.g. "VII. Csányi utca"),
so this is wired up as an "exact" precision source like alberlet.hu, and
no per-listing detail-page fetch is needed.

This agency lists both rentals and sales. Sale listings are skipped via
their URL slug (which reliably contains "elado" = for-sale); as a second
line of defense, sale prices are quoted in millions ("X millió Ft"),
which config.MAX_RENT_HUF's price parser in filters.py won't recognize as
a plain rental amount anyway, so one slipping past the slug check would
still fail the hard price filter.

Caveat: the excerpt text used for soft filters (furnished/terrace/move-in
date) is WordPress's auto-truncated preview, not the full listing body —
same category of limitation as the other sources here that only read
list-page text (albifigyelo.hu, megveszlak.hu, rentola.hu). A missing
detail just means "verify manually", not a false negative.
"""

import re
from typing import List

import requests
from bs4 import BeautifulSoup

from models import Listing

SEARCH_URL = "https://tappancsosotthon.hu/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

_PROPERTY_ID_RE = re.compile(r'data-property-id="(\d+)"')


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[tappancsosotthon.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    seen_ids = set()

    for card in soup.find_all("div", class_="property-item"):
        title_link = card.select_one("h2.property-title a")
        if not title_link or not title_link.get("href"):
            continue

        url = title_link["href"]
        if "elado" in url.lower():
            continue  # for-sale listing, not a rental

        id_match = _PROPERTY_ID_RE.search(str(card))
        listing_id = id_match.group(1) if id_match else url
        if listing_id in seen_ids:
            continue
        seen_ids.add(listing_id)

        title = title_link.get_text(strip=True)

        price_el = card.select_one("span.property-price")
        price_text = price_el.get_text(strip=True) if price_el else ""

        excerpt_el = card.select_one("div.property-excerpt")
        excerpt_text = excerpt_el.get_text(" ", strip=True) if excerpt_el else ""

        size_sqm = _first_number(card, ".property-area .property-info-value")
        rooms = _first_number(card, ".property-bedrooms .property-info-value")

        listings.append(Listing(
            source="tappancsosotthon.hu",
            listing_id=listing_id,
            url=url,
            title=title,
            price_text=price_text,
            size_sqm=size_sqm,
            rooms=rooms,
            address_text=title,
            description_text=f"{title} {excerpt_text}",
        ))

    return listings


def _first_number(card, selector):
    el = card.select_one(selector)
    if not el:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)", el.get_text())
    return float(match.group(1).replace(",", ".")) if match else None
