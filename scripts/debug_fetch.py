"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

Round 4 (oc.hu): the Playwright capture showed the search form actually
navigates to a plain GET URL using semicolon/tilde path segments:
https://www.oc.hu/ingatlanok/lista/ertekesites:kiado;meret:40~;szoba:2~
(min-only ranges use a trailing ~). Confirm this is a real, filterable,
plain-requests-fetchable URL and inspect its listing card markup.

Round 3 (megveszlak.hu): dig into the exact card markup around
hirdetes_item_ar/cim/meretekdiv classes found on /alberlet-budapest, and
check whether pagination (?Oldal=2) and a per-district URL work.
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


def dump_oc():
    url = "https://www.oc.hu/ingatlanok/lista/ertekesites:kiado;meret:40~;szoba:2~"
    print("=" * 80)
    print(f"GET {url}")
    resp = get(url)
    html = resp.text
    print(f"status={resp.status_code} final_url={resp.url}")
    print(f"content length: {len(html)}")
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    total_count = re.findall(r'(\d[\d\s]{0,8})\s*(?:db|találat)', html, re.IGNORECASE)
    print(f"possible result-count numbers: {total_count[:10]}")

    hrefs = re.findall(r'href="([^"]+)"', html)
    listing_hrefs = sorted(set(h for h in hrefs if re.search(r"/ingatlanok/H\d+", h)))
    print(f"unique /ingatlanok/H* hrefs found: {len(listing_hrefs)}")
    for h in listing_hrefs[:15]:
        print(f"  {h}")

    # dump full card block around the first listing anchor, further than before,
    # to find where price/address/room-count text sits within the card.
    m = re.search(r'href="(/ingatlanok/H\d+)"', html)
    if m:
        start = max(0, m.start() - 100)
        end = min(len(html), m.end() + 3000)
        print("--- full card HTML window ---")
        print(html[start:end])


def dump_megveszlak():
    print("=" * 80)
    url = "https://megveszlak.hu/alberlet-budapest"
    print(f"GET {url}")
    resp = get(url)
    html = resp.text
    print(f"status={resp.status_code}")

    m = re.search(r'class="hirdetes_item_ar"', html)
    if m:
        start = max(0, m.start() - 800)
        end = min(len(html), m.end() + 1500)
        print("--- full card HTML window around first hirdetes_item_ar ---")
        print(html[start:end])

    print("=" * 80)
    url2 = "https://megveszlak.hu/alberlet-budapest?Oldal=2"
    print(f"GET {url2}")
    resp2 = get(url2)
    print(f"status={resp2.status_code}")
    hrefs2 = re.findall(r'href="(/hirdetes/[^"]+)"', resp2.text)
    print(f"page 2 listing hrefs found: {len(set(hrefs2))} (sample 5): {sorted(set(hrefs2))[:5]}")

    print("=" * 80)
    url3 = "https://megveszlak.hu/alberlet-budapest-ix-kerulet"
    print(f"GET {url3}")
    resp3 = get(url3)
    print(f"status={resp3.status_code} final_url={resp3.url}")
    if resp3.status_code == 200:
        title_match = re.search(r"<title>(.*?)</title>", resp3.text, re.IGNORECASE | re.DOTALL)
        print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")


if __name__ == "__main__":
    dump_oc()
    dump_megveszlak()
