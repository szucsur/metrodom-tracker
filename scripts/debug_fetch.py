"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

Round 3: the working rental search URL is
https://www.oc.hu/index.php/ingatlanok/lista/ertekesites:kiado (chaining
more path segments like /tipus:lakas redirects away and loses the "kiado"
filter, so filtering must happen in Python like every other source here).
This round dumps the raw HTML around each listing-card anchor on that page
to find price/size/room/address markup, and fetches one real rental detail
page (H521686) to see its structure.
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

LIST_URL = "https://www.oc.hu/index.php/ingatlanok/lista/ertekesites:kiado"
DETAIL_URL = "https://www.oc.hu/ingatlanok/H521686"


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def dump_list_page():
    print("=" * 80)
    print(f"GET {LIST_URL}")
    html = fetch(LIST_URL)
    print(f"content length: {len(html)}")

    # Find all listing card anchors and print a window of HTML around each
    for match in re.finditer(r'href="(/ingatlanok/H\d+)"', html):
        start = max(0, match.start() - 200)
        end = min(len(html), match.end() + 900)
        print("-" * 60)
        print(html[start:end])

    # look for a repeating card container class name
    class_matches = re.findall(r'class="([^"]*card[^"]*)"', html, re.IGNORECASE)
    print(f"classes containing 'card' (sample): {class_matches[:10]}")
    result_classes = re.findall(r'class="([^"]*result[^"]*)"', html, re.IGNORECASE)
    print(f"classes containing 'result' (sample): {result_classes[:10]}")

    # pagination clues
    page_hrefs = re.findall(r'href="([^"]*oldal[^"]*)"', html, re.IGNORECASE)
    print(f"pagination-like hrefs (sample): {page_hrefs[:10]}")
    total_count = re.findall(r'(\d+)\s*(?:db|találat)', html, re.IGNORECASE)
    print(f"possible result-count numbers: {total_count[:10]}")


def dump_detail_page():
    print("=" * 80)
    print(f"GET {DETAIL_URL}")
    html = fetch(DETAIL_URL)
    print(f"content length: {len(html)}")
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    # dump JSON-LD blocks with @type != FAQPage
    ldjson_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for i, block in enumerate(ldjson_blocks):
        if "FAQPage" not in block:
            print(f"non-FAQ JSON-LD block[{i}] (first 1000 chars): {block.strip()[:1000]}")

    # print context around price / address / size / rooms
    for keyword in ["Ft/hó", "cím", "Cím", "Terület", "Szobák", "szoba"]:
        idx = html.find(keyword)
        if idx != -1:
            print(f"--- context around '{keyword}' ---")
            print(html[max(0, idx - 200):idx + 300])


if __name__ == "__main__":
    dump_list_page()
    dump_detail_page()
