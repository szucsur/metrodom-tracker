#!/usr/bin/env python3
"""One-off diagnostic: fetch candidate URLs and report status + a body
snippet, so real site behavior can be inspected from an environment that
actually has internet access (this sandbox does not). Not part of the
regular tracker run."""

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

CANDIDATES = [
    "https://www.alberlet.hu/kiado-lakas/budapest-ix-kerulet",
]


def inspect_alberlet_cards(html: str):
    import re

    print(f"  total length: {len(html)}")
    # Find occurrences of Hungarian rent price pattern "... Ft/hó" for context.
    for m in list(re.finditer(r"Ft\s*/\s*h[oó]", html, re.IGNORECASE))[:3]:
        start = max(0, m.start() - 400)
        end = min(len(html), m.end() + 100)
        print("  --- context around a price match ---")
        print("  " + html[start:end].replace("\n", " "))
    price_count = len(re.findall(r"Ft\s*/\s*h[oó]", html, re.IGNORECASE))
    print(f"  total 'Ft/hó' occurrences: {price_count}")

    # Class names that appear right before a price match, as selector candidates.
    class_hits = re.findall(r'class="([^"]{0,60})"[^<]{0,300}?Ft\s*/\s*h[oó]', html, re.IGNORECASE)
    print(f"  candidate class attrs near price: {class_hits[:10]}")

    # Any listing-detail-looking links.
    hrefs = re.findall(r'href="([^"]*(?:hirdetes|kiado-lakas)[^"]*)"', html, re.IGNORECASE)
    print(f"  sample hrefs matching listing pattern (first 10 of {len(hrefs)}): {hrefs[:10]}")


def main():
    session = requests.Session()
    for url in CANDIDATES:
        print("=" * 70)
        print(f"URL: {url}")
        try:
            resp = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        except requests.RequestException as exc:
            print(f"  request failed: {exc}")
            continue
        print(f"  final url: {resp.url}")
        print(f"  status: {resp.status_code}")
        inspect_alberlet_cards(resp.text)


if __name__ == "__main__":
    main()
