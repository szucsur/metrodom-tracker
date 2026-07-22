"""Scraper for rentola.hu — an international rental-listing platform
(Hungarian edition of a multi-country site).

The Budapest apartments page embeds every listing shown as clean
JSON-LD (schema.org SearchResultsPage -> ItemList -> RealEstateListing),
including a real streetAddress field — unlike albifigyelo.hu, this
source does expose the actual street name, so it's wired up as an
"exact" location match like ingatlan.com/alberlet.hu/flatco.hu, not the
district-only fallback used for albifigyelo.hu.

Caveat: the page's default sort is "Ajánlott" (Recommended), not
strictly newest-first, and only the first batch of listings (~10-20) is
present in the initial page load's JSON-LD — no pagination is followed.
Since matches are rare (a specific street), there's a small chance a
brand new listing could be sorted past the first page before an hourly
check catches it. No site-side sort/filter parameter was found during
inspection; if this turns out to matter in practice, revisit sort
options on the live site.
"""

import json
import re
from typing import List

import requests

from models import Listing

SEARCH_URL = "https://rentola.hu/kiado/lakasok/budapest"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[rentola.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    listings = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if data.get("@type") != "SearchResultsPage":
            continue
        items = data.get("mainEntity", {}).get("itemListElement", [])
        for entry in items:
            listing = _listing_from_item(entry)
            if listing:
                listings.append(listing)
    return listings


def _listing_from_item(entry: dict) -> Listing:
    url = entry.get("url") or ""
    item = entry.get("item") or {}
    if item.get("@type") != "RealEstateListing" or not url:
        return None

    match = re.search(r"-p([0-9a-f]+)$", url)
    listing_id = match.group(1) if match else url

    title = item.get("name") or ""
    offers = item.get("offers") or {}
    price = offers.get("price")
    currency = offers.get("priceCurrency", "")
    price_text = f"{price} {currency}/hónap" if price is not None else ""
    posted_at = offers.get("validFrom")

    offered = offers.get("itemOffered") or {}
    address = (offered.get("address") or {}).get("streetAddress", "")
    size_sqm = (offered.get("floorSize") or {}).get("value")
    rooms = (offered.get("numberOfBedrooms") or {}).get("value")

    return Listing(
        source="rentola.hu",
        listing_id=listing_id,
        url=url,
        title=title,
        price_text=price_text,
        size_sqm=float(size_sqm) if size_sqm is not None else None,
        rooms=float(rooms) if rooms is not None else None,
        address_text=address,
        description_text=f"{title} {address}",
        posted_at=posted_at,
    )
