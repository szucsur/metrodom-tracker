"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

Round 6 (oc.hu): the card HTML contains an HTML-entity-escaped JSON blob
(looks like a Symfony UX Live Component props value — has base_reg_nr, url,
slogen, @attributes, @checksum keys) that likely holds the FULL listing
record (address, price, size, rooms) server-rendered right there on the
list page — no per-listing detail-page fetch needed if so. This locates the
attribute, unescapes it, and dumps its keys.
"""

import html as html_module
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


def get(url):
    return requests.get(url, headers=HEADERS, timeout=20)


def dump_oc():
    url = "https://www.oc.hu/ingatlanok/lista/ertekesites:kiado;meret:40~;szoba:2~"
    print("=" * 80)
    print(f"GET {url}")
    resp = get(url)
    html_text = resp.text
    print(f"status={resp.status_code}")

    # find every attribute value that contains base_reg_nr (the live-component props blob)
    for m in re.finditer(r'([a-zA-Z0-9_-]+)="([^"]*base_reg_nr[^"]*)"', html_text):
        attr_name, raw_value = m.group(1), m.group(2)
        print(f"found attribute: {attr_name} (raw length {len(raw_value)})")
        unescaped = html_module.unescape(raw_value)
        # the value itself may be JSON with escaped unicode like é already literal after html unescape
        try:
            data = json.loads(unescaped)
            print("Parsed as JSON! Top-level keys:", list(data.keys()) if isinstance(data, dict) else type(data))
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
        except json.JSONDecodeError as exc:
            print(f"not directly parseable as JSON ({exc}); first 1500 chars of unescaped value:")
            print(unescaped[:1500])
        print("-" * 60)


if __name__ == "__main__":
    dump_oc()
