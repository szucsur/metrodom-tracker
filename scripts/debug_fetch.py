"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

Round 5 (oc.hu): the filtered URL
https://www.oc.hu/ingatlanok/lista/ertekesites:kiado;meret:40~;szoba:2~
works and returns 11 pre-filtered (>=40m2, >=2 room) listings, but the
window captured after the card anchor was just an image carousel — the
price/address/size text sits BEFORE the <a href="/ingatlanok/H...">, in the
h4 block. This grabs a window before each anchor instead.

Round (megveszlak.hu): check whether a listing DETAIL page exposes the
actual street name (list page only ever showed district, e.g. "Budapest V.
kerület, Belváros") — if so this source can be "exact" precision like
alberlet.hu instead of "district" precision like albifigyelo.hu.
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
    print(f"status={resp.status_code}")

    for m in re.finditer(r'href="(/ingatlanok/H\d+)"', html):
        start = max(0, m.start() - 2500)
        print("-" * 60)
        print(f"card for {m.group(1)}:")
        print(html[start:m.start() + 40])
        break  # just need one full example


def dump_megveszlak():
    print("=" * 80)
    url = "https://megveszlak.hu/hirdetes/kiado-lakas-budapest-ix-kerulet-98544534"
    print(f"GET {url}")
    resp = get(url)
    html = resp.text
    print(f"status={resp.status_code} final_url={resp.url}")
    print(f"content length: {len(html)}")

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    # look for any street-name-bearing text/hidden fields
    for keyword in ["cím", "Cím", "utca", "út ", "körút", "tér "]:
        idx = html.find(keyword)
        if idx != -1:
            print(f"--- context around '{keyword}' ---")
            print(html[max(0, idx - 200):idx + 300])

    # check for JSON-LD / map coordinates
    ldjson_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    print(f"JSON-LD blocks: {len(ldjson_blocks)}")
    for i, block in enumerate(ldjson_blocks):
        print(f"  block[{i}] first 500 chars: {block.strip()[:500]}")

    lat_lng = re.findall(r'(lat|lng|latitude|longitude)["\']?\s*[:=]\s*["\']?(-?\d+\.\d+)', html, re.IGNORECASE)
    print(f"lat/lng-like matches: {lat_lng[:5]}")


if __name__ == "__main__":
    dump_oc()
    dump_megveszlak()
