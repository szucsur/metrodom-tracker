"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

Round 2 for megveszlak.hu: the homepage exposed a direct nav link
/alberlet-budapest (a rental listing page for Budapest specifically, plus
per-city variants like /alberlet-pecs). This inspects that page's markup —
listing card structure, price/size/room text, any district/street filter
params, JSON-LD, and pagination — to figure out how to parse it.
"""

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

LIST_URL = "https://megveszlak.hu/alberlet-budapest"


def dump():
    print("=" * 80)
    print(f"GET {LIST_URL}")
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=20)
    print(f"status={resp.status_code} final_url={resp.url}")
    html = resp.text
    print(f"content length: {len(html)}")

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    ldjson_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD script blocks found: {len(ldjson_blocks)}")
    for i, block in enumerate(ldjson_blocks):
        types = re.findall(r'"@type"\s*:\s*"([^"]+)"', block)
        print(f"  block[{i}] @type values: {types[:5]} (len={len(block)})")
        if "RealEstate" in block or "ItemList" in block:
            print(f"    first 800 chars: {block.strip()[:800]}")

    print(f"'Ft/hó' occurrences: {html.count('Ft/hó')}")
    print(f"'Ft /hó' occurrences: {html.count('Ft /hó')}")
    print(f"'m²' occurrences: {html.count('m²')}")
    print(f"'szoba' occurrences: {html.lower().count('szoba')}")
    print(f"'vágóhíd' (case-insens) occurrences: {html.lower().count('vágóhíd')}")
    print(f"'metrodom' (case-insens) occurrences: {html.lower().count('metrodom')}")
    print(f"'ix. ker' (case-insens) occurrences: {html.lower().count('ix. ker')}")
    print(f"'ferencváros' (case-insens) occurrences: {html.lower().count('ferencváros')}")

    # listing detail links: guess pattern from hrefs with digits
    hrefs = re.findall(r'href="([^"]+)"', html)
    print(f"total hrefs: {len(hrefs)}")
    digit_hrefs = [h for h in hrefs if re.search(r"\d{3,}", h)]
    seen = set()
    count = 0
    print("digit-bearing hrefs (sample up to 20):")
    for h in digit_hrefs:
        if h in seen:
            continue
        seen.add(h)
        print(f"  {h}")
        count += 1
        if count >= 20:
            break

    # pagination / district filter clues
    kerulet_hrefs = [h for h in hrefs if "kerulet" in h.lower() or "ker" in h.lower()]
    print(f"hrefs mentioning kerulet (sample up to 10): {kerulet_hrefs[:10]}")
    page_hrefs = [h for h in hrefs if "oldal" in h.lower() or "page" in h.lower()]
    print(f"pagination-like hrefs (sample up to 10): {page_hrefs[:10]}")

    # dump context around first szoba occurrence (likely inside a listing card)
    idx = html.lower().find("szoba")
    if idx != -1:
        print("--- context around first 'szoba' ---")
        print(html[max(0, idx - 400):idx + 400])

    # dump context around first m² occurrence
    idx2 = html.find("m²")
    if idx2 != -1:
        print("--- context around first 'm²' ---")
        print(html[max(0, idx2 - 400):idx2 + 200])

    # look for a repeating card container class
    class_matches = re.findall(r'class="([^"]*(?:card|item|listing|result)[^"]*)"', html, re.IGNORECASE)
    print(f"classes containing card/item/listing/result (sample up to 15): {class_matches[:15]}")


if __name__ == "__main__":
    dump()
