#!/usr/bin/env python3
"""One-off diagnostic: dump the full JSON-LD SearchResultsPage structure
from rentola.hu's Budapest apartments page, to see every field available
per listing (address, size, rooms, price). Not part of the regular
tracker run."""

import json
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
    resp = requests.get("https://rentola.hu/kiado/lakasok/budapest", headers=HEADERS, timeout=20)
    html = resp.text
    print(f"status: {resp.status_code}; length: {len(html)}")

    scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD blocks: {len(scripts)}")

    for s in scripts:
        try:
            data = json.loads(s)
        except json.JSONDecodeError as exc:
            print(f"  JSON parse failed: {exc}")
            continue
        if data.get("@type") != "SearchResultsPage":
            continue
        items = data.get("mainEntity", {}).get("itemListElement", [])
        print(f"itemListElement count: {len(items)}")
        for item in items[:3]:
            print("--- item ---")
            print(json.dumps(item, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
