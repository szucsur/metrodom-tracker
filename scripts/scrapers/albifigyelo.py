"""Scraper for albifigyelo.hu — a nationwide rental-listing aggregator
(not the original poster; it credits a "Forrás:" / source site like
ingatlan.com, jofogas.hu, ingatlanbazar.hu, zenga.hu per listing).

Important limitation, confirmed by inspecting both the visible page and
the structured (JSON-LD) data: albifigyelo.hu only ever exposes
district/neighborhood-level location (e.g. "Budapest, Kelenföld" or
"Budapest VII. kerület") — never a street name, not even in hidden
schema.org data (only country + city + GPS coordinates). So this source
is wired up as a *district-level* watch (Listing.location_precision =
"district"): it will match on "IX. kerület" alone rather than requiring
"Vágóhíd" text, and filters.py flags these as needing manual street
confirmation via the source link.

The Budapest listing page (sorted newest-first by default) is
server-rendered with a manageable first batch of listings — no site-side
district/price/room filtering is needed since that all happens in
Python via filters.py, same as every other source.
"""

import re
from typing import List

import requests
from bs4 import BeautifulSoup

from models import Listing

SEARCH_URL = "https://albifigyelo.hu/kiado-alberletek/budapest"
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
        print(f"[albifigyelo.hu] request failed: {exc}")
        return []

    return _parse_listings(resp.text)


def _parse_listings(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for info in soup.find_all("div", class_="itemInfos"):
        item_link = info.find_parent("a")
        if not item_link:
            continue
        detail_link = item_link.find_next_sibling("a", class_="adDetails")
        if not detail_link or not detail_link.get("href"):
            continue

        href = detail_link["href"]
        match = re.search(r"/hirdetesek/(\d+)", href)
        if not match:
            continue
        listing_id = match.group(1)

        price_el = info.find("h2", class_="price")
        price_text = price_el.get_text(strip=True) if price_el else ""

        title_el = info.find("div", class_="adTitle")
        title = title_el.get_text(strip=True) if title_el else ""

        size_sqm = rooms = None
        props = info.find("div", class_="properties")
        if props:
            for div in props.find_all("div", recursive=False):
                text = div.get_text(strip=True)
                size_match = re.match(r"(\d+)\s*m", text)
                rooms_match = re.match(r"(\d+)\s*szoba", text, re.IGNORECASE)
                if size_match:
                    size_sqm = float(size_match.group(1))
                elif rooms_match:
                    rooms = float(rooms_match.group(1))

        # Site/source div is a sibling of detail_link, not of item_link.
        site_div = detail_link.find_next_sibling("div", class_="site")
        source_text = site_div.get_text(strip=True) if site_div else ""

        listings.append(Listing(
            source="albifigyelo.hu",
            listing_id=listing_id,
            url=href,
            title=title,
            price_text=price_text,
            size_sqm=size_sqm,
            rooms=rooms,
            address_text=title,
            description_text=f"{title} {source_text}",
            location_precision="district",
        ))

    return listings
