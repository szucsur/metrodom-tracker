#!/usr/bin/env python3
"""One-off diagnostic: look for an underlying API/AJAX endpoint behind
albifigyelo.hu's filter UI (price/rooms/area inputs have no `name`
attrs, suggesting JS-driven filtering), and count how many listing
cards are actually present in the raw HTML vs. loaded dynamically.
Not part of the regular tracker run."""

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
    resp = requests.get("https://albifigyelo.hu/kiado-alberletek/budapest", headers=HEADERS, timeout=20)
    html = resp.text
    print(f"status: {resp.status_code}; length: {len(html)}")

    # Count actual listing detail hrefs present in raw HTML.
    hrefs = set(re.findall(r'href="(https://albifigyelo\.hu/hirdetesek/\d+)"', html))
    print(f"unique listing hrefs in raw HTML: {len(hrefs)}")

    # Look for API/AJAX/JSON config markers.
    for marker in ["api.albifigyelo", "/api/", "fetch(", "axios", "window.__", "data-api",
                   "application/json", "graphql", "algolia", "meilisearch", "typesense"]:
        count = html.lower().count(marker.lower())
        if count:
            print(f"marker {marker!r}: {count} occurrence(s)")

    # Dump inline script blocks that look like config (contain 'kerulet' or 'district' or 'filter').
    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.IGNORECASE | re.DOTALL)
    print(f"inline script blocks: {len(scripts)}")
    for s in scripts:
        if re.search(r"kerulet|district|filter|api", s, re.IGNORECASE) and len(s.strip()) > 100:
            print("--- relevant inline script snippet (first 800 chars) ---")
            print(s.strip()[:800])

    # Dump external script src attributes (helps spot the framework/bundle).
    srcs = re.findall(r'<script[^>]+src="([^"]+)"', html, re.IGNORECASE)
    print(f"script src count: {len(srcs)}")
    for s in srcs:
        if "albifigyelo" in s or s.startswith("/"):
            print(f"  {s}")


if __name__ == "__main__":
    main()
