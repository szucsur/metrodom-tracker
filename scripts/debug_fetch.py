#!/usr/bin/env python3
"""One-off diagnostic: check whether albifigyelo.hu exposes a
street-level address anywhere in a listing detail page's raw HTML
(schema.org address, meta tags, map data attributes, etc.), since the
visible text only ever showed district-level location. Not part of the
regular tracker run."""

import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}


def main():
    resp = requests.get("https://albifigyelo.hu/hirdetesek/58206719", headers=HEADERS, timeout=20)
    html = resp.text
    print(f"status: {resp.status_code}; length: {len(html)}")

    for marker in ["streetAddress", "PostalAddress", "utca", "\"address\"", "geo", "latitude",
                   "data-lat", "data-lng", "og:street", "cim", "vágóhíd", "vagohid"]:
        count = html.lower().count(marker.lower())
        if count:
            print(f"marker {marker!r}: {count} occurrence(s)")
            idx = html.lower().find(marker.lower())
            print(f"  context: ...{html[max(0,idx-150):idx+150]}...")

    # Dump all JSON-LD script blocks in full (small enough to be useful).
    scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD blocks: {len(scripts)}")
    for s in scripts:
        print("--- JSON-LD ---")
        print(s.strip()[:1500])


if __name__ == "__main__":
    main()
