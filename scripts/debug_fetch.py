"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

This round: initial reconnaissance of megveszlak.hu (brand new source, not
yet investigated at all) — status code, title, Cloudflare check, JSON-LD,
and candidate listing link patterns, same first pass used for every other
source in this project.
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

CANDIDATE_URLS = [
    "https://www.megveszlak.hu/",
    "https://megveszlak.hu/",
]


def dump(url):
    print("=" * 80)
    print(f"GET {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"REQUEST FAILED: {exc}")
        return
    print(f"status={resp.status_code} final_url={resp.url}")
    print(f"server={resp.headers.get('server')}")
    html = resp.text
    print(f"content length: {len(html)}")

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    print(f"'cloudflare' in headers: {'cloudflare' in str(resp.headers).lower()}")
    print(f"'Just a moment' in html: {'Just a moment' in html}")
    print(f"'Attention Required' in html: {'Attention Required' in html}")

    ldjson_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD script blocks found: {len(ldjson_blocks)}")
    for i, block in enumerate(ldjson_blocks[:3]):
        print(f"  block[{i}] first 300 chars: {block.strip()[:300]}")

    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    print(f"__NEXT_DATA__ present: {bool(next_data)}")

    print(f"'kiad' (case-insens) occurrences: {html.lower().count('kiad')}")
    print(f"'elad' (case-insens) occurrences: {html.lower().count('elad')}")
    print(f"'bérl' (case-insens) occurrences: {html.lower().count('bérl')}")
    print(f"'m²' occurrences: {html.count('m²')}")
    print(f"'szoba' occurrences: {html.lower().count('szoba')}")

    hrefs = re.findall(r'href="([^"]+)"', html)
    print(f"total hrefs: {len(hrefs)}")
    listing_like = [h for h in hrefs if re.search(r"/\d{4,}", h)]
    print(f"digit-ID-like hrefs (sample up to 15):")
    seen = set()
    count = 0
    for h in listing_like:
        if h in seen:
            continue
        seen.add(h)
        print(f"  {h}")
        count += 1
        if count >= 15:
            break

    forms = re.findall(r"<form[^>]*action=\"([^\"]*)\"[^>]*>", html)
    print(f"form actions found: {forms[:10]}")

    nav_search_links = [h for h in hrefs if "kiad" in h.lower() or "berl" in h.lower()]
    print(f"nav links containing 'kiad'/'berl' (sample up to 10):")
    for h in nav_search_links[:10]:
        print(f"  {h}")


if __name__ == "__main__":
    for url in CANDIDATE_URLS:
        dump(url)
