"""Scraper for oc.hu — Otthon Centrum, a nationwide real-estate agency
franchise network.

The rental search page is built with Symfony UX Live Components: plain
query-string parameters on the URL don't filter anything (confirmed by
inspecting the network requests a real search-form submission fires — the
total result count stayed identical regardless of query params). The form
actually navigates the browser to a plain GET URL using semicolon/tilde
path segments, e.g.:

    https://www.oc.hu/ingatlanok/lista/ertekesites:kiado;meret:40~;szoba:2~

("meret:40~" = minimum size 40, open-ended; "szoba:2~" = minimum 2 rooms).
That URL is server-rendered and fetchable with a plain GET — no browser
needed at runtime.

Each listing card embeds its full record as an HTML-entity-escaped JSON
blob in a `data-live-props-value` attribute (a Symfony UX Live Component
props value), containing price/size/rooms and a free-text description —
so this parses that JSON directly rather than scraping visible card text.

Caveat: oc.hu's own structured `location`/`district` fields are only ever
district/city-level (e.g. "Budapest III. kerület" / "Aranyhegy"), never a
street name — same limitation as albifigyelo.hu and megveszlak.hu. Unlike
those two, though, oc.hu's free-text `description` is agent-written prose
that in practice names the actual street/landmark (every sample listing
inspected did), so this is still wired up as "exact" precision like
alberlet.hu/flatco.hu/rentola.hu: filters.py's location_matches() requires
the street name itself to appear in the combined text, same rigor as
those other exact-precision sources.
"""

import html as html_module
import json
import re
from typing import List

import requests

import config
from models import Listing

SEARCH_URL = (
    f"https://www.oc.hu/ingatlanok/lista/"
    f"ertekesites:kiado;meret:{config.MIN_SIZE_SQM}~;szoba:{config.MIN_ROOMS}~"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

_PROPS_ATTR_RE = re.compile(r'data-live-props-value="([^"]*base_reg_nr[^"]*)"')
_NUMBER_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[oc.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    listings = []
    for match in _PROPS_ATTR_RE.finditer(html):
        try:
            data = json.loads(html_module.unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        listing = _listing_from_record(data.get("record") or {})
        if listing:
            listings.append(listing)
    return listings


def _first_number(text: str):
    m = _NUMBER_RE.search(text or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _listing_from_record(record: dict) -> Listing:
    reg_nr = record.get("reg_nr") or record.get("base_reg_nr")
    url = record.get("url")
    if not reg_nr or not url:
        return None

    title = record.get("slogen") or reg_nr
    location = record.get("location") or ""
    district = record.get("district") or ""
    description = record.get("description") or ""
    address_text = f"{location} {district}".strip()

    return Listing(
        source="oc.hu",
        listing_id=reg_nr,
        url=f"https://www.oc.hu{url}",
        title=title,
        price_text=record.get("price") or "",
        size_sqm=_first_number(record.get("size")),
        rooms=_first_number(record.get("rooms")),
        address_text=address_text,
        description_text=f"{title} {address_text} {description}",
    )
