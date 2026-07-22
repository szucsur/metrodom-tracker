"""Scraper for rentingo.com search results.

Confirmed (via direct GitHub Actions runner requests, not just guessing):
rentingo.com sits behind a Cloudflare bot-challenge page
("Attention Required! | Cloudflare") that returns HTTP 403 to automated
requests, regardless of header set used (tested both a minimal header
set and a fuller browser-like one — same block either time). This is an
active anti-bot wall, not a wrong-URL or missing-header problem, and
getting past it reliably would require the same kind of anti-bot evasion
(headless-browser fingerprint spoofing to pass the challenge) this
project deliberately avoids for Facebook and ingatlan.com too.

This module still attempts a plain request each run — in case
Cloudflare's rules change — but expect it to consistently return zero
listings.

**For rentingo.com coverage, use its own saved-search email alerts
instead**: run the search on the site, save it, and enable notifications.
"""

from typing import List

import requests

from models import Listing

SEARCH_URL = "https://rentingo.com/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(SEARCH_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(
            f"[rentingo.com] request failed (expected — Cloudflare-blocked, "
            f"see module docstring): {exc}"
        )
        return []

    # If this ever succeeds, rentingo.com's markup hasn't been inspected
    # yet — this is a placeholder that would need real selectors written
    # against the actual (currently unreachable) search-results page.
    print("[rentingo.com] request unexpectedly succeeded — Cloudflare rules "
          "may have changed. Parsing not implemented yet; inspect the page "
          "and update this scraper.")
    return []
