"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

Round 2: oc.hu's homepage confirmed reachable (not Cloudflare-blocked), with
a search form posting to /index.php/ingatlanok/kereses and a rental listing
nav link /index.php/ingatlanok/lista/ertekesites:kiado. Individual listings
look like /ingatlanok/H521592. This round probes the rental list URL (with
and without district/query params) and a couple of listing detail pages to
see actual markup shape.
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
    "https://www.oc.hu/index.php/ingatlanok/lista/ertekesites:kiado",
    "https://www.oc.hu/index.php/ingatlanok/lista/ertekesites:kiado/tipus:lakas",
    "https://www.oc.hu/index.php/ingatlanok/lista/ertekesites:kiado/tipus:lakas/telepules:budapest",
    "https://www.oc.hu/index.php/ingatlanok/kereses?ertekesites=kiado&tipus=lakas&telepules=budapest&kerulet=9",
    "https://www.oc.hu/ingatlanok/H521592",
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
    html = resp.text
    print(f"content length: {len(html)}")

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    ldjson_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD script blocks found: {len(ldjson_blocks)}")
    for i, block in enumerate(ldjson_blocks):
        types = re.findall(r'"@type"\s*:\s*"([^"]+)"', block)
        print(f"  block[{i}] @type values: {types[:5]} (len={len(block)})")

    print(f"'Ft/hó' occurrences: {html.count('Ft/hó')}")
    print(f"'Ft /hó' occurrences: {html.count('Ft /hó')}")
    print(f"'/hó' occurrences: {html.count('/hó')}")
    print(f"'m²' occurrences: {html.count('m²')}")
    print(f"'szoba' occurrences: {html.lower().count('szoba')}")
    print(f"'vágóhíd' (case-insens) occurrences: {html.lower().count('vágóhíd')}")
    print(f"'metrodom' (case-insens) occurrences: {html.lower().count('metrodom')}")
    print(f"'ix. ker' (case-insens) occurrences: {html.lower().count('ix. ker')}")

    hrefs = re.findall(r'href="([^"]+)"', html)
    listing_like = [h for h in hrefs if re.search(r"/ingatlanok/H\d+", h)]
    print(f"total hrefs: {len(hrefs)}, /ingatlanok/H* hrefs found: {len(listing_like)} (sample up to 10):")
    seen = set()
    count = 0
    for h in listing_like:
        if h in seen:
            continue
        seen.add(h)
        print(f"  {h}")
        count += 1
        if count >= 10:
            break

    # Look for query-string / pagination hints, filter widget option values
    kerulet_options = re.findall(r'value="(9|IX)"[^>]*>([^<]{0,40})', html)
    print(f"possible kerulet=9/IX option matches: {kerulet_options[:5]}")

    # dump a text snippet around first szoba/m2 occurrence for card structure clues
    idx = html.lower().find("szoba")
    if idx != -1:
        print("context around first 'szoba':")
        print(html[max(0, idx - 300):idx + 300])


if __name__ == "__main__":
    for url in CANDIDATE_URLS:
        dump(url)
