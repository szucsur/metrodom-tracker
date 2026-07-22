"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

Round 2: tappancsosotthon.hu ("Rent with Paws") is a small pet-friendly
rental agency in Budapest, WordPress-based, with listings at
/property/{slug}/. This inspects the homepage's listing card markup (CSS
classes, JSON-LD, pagination) to write a real scraper.
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


def get(url):
    return requests.get(url, headers=HEADERS, timeout=20)


def dump_home():
    url = "https://tappancsosotthon.hu/"
    print("=" * 80)
    print(f"GET {url}")
    resp = get(url)
    html = resp.text
    print(f"status={resp.status_code}, content length: {len(html)}")

    ldjson_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD blocks found: {len(ldjson_blocks)}")
    for i, block in enumerate(ldjson_blocks):
        types = re.findall(r'"@type"\s*:\s*"([^"]+)"', block)
        print(f"  block[{i}] @type: {types[:5]} (len={len(block)})")

    hrefs = re.findall(r'href="(https://tappancsosotthon\.hu/property/[^"]+)"', html)
    unique_hrefs = sorted(set(hrefs))
    print(f"property hrefs found: {len(unique_hrefs)}")
    for h in unique_hrefs[:15]:
        print(f"  {h}")

    # dump raw HTML window around the first property link to see card structure
    m = re.search(r'href="(https://tappancsosotthon\.hu/property/[^"]+)"', html)
    if m:
        start = max(0, m.start() - 1500)
        end = min(len(html), m.end() + 2500)
        print("--- card HTML window ---")
        print(html[start:end])

    # pagination
    page_hrefs = re.findall(r'href="([^"]*page[^"]*)"', html, re.IGNORECASE)
    print(f"pagination-like hrefs (sample): {sorted(set(page_hrefs))[:10]}")

    class_matches = re.findall(r'class="([^"]*(?:property|listing|post|card)[^"]*)"', html, re.IGNORECASE)
    print(f"classes containing property/listing/post/card (sample up to 20): {class_matches[:20]}")


def dump_detail():
    url = "https://tappancsosotthon.hu/property/vii-csanyi-utca/"
    print("=" * 80)
    print(f"GET {url}")
    resp = get(url)
    html = resp.text
    print(f"status={resp.status_code}, content length: {len(html)}")

    ldjson_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD blocks found: {len(ldjson_blocks)}")
    for i, block in enumerate(ldjson_blocks):
        print(f"  block[{i}] first 800 chars: {block.strip()[:800]}")

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    for keyword in ["Ft", "m2", "m²", "szoba", "Cím", "cím", "Erkély", "erkély", "Bútorozott", "bútorozott", "Költözhető", "költözhető"]:
        idx = html.find(keyword)
        if idx != -1:
            print(f"--- context around '{keyword}' ---")
            print(html[max(0, idx - 150):idx + 250])


if __name__ == "__main__":
    dump_home()
    dump_detail()
