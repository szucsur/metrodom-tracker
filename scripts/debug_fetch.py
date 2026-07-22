#!/usr/bin/env python3
"""One-off diagnostic: check whether the real alberlet.hu search-results
URL (discovered via the Playwright-driven UI flow) renders content via a
plain HTTP GET, or requires JS execution. Not part of the regular
tracker run."""

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

URL = "https://www.alberlet.hu/kiado-alberlet?ingatlan-tipus=lakas&kerulet=ix&meret=40-x-m2&szoba=2-x&keres=normal&limit=24"


def main():
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    print(f"status: {resp.status_code}")
    html = resp.text
    print(f"length: {len(html)}")
    ft_count = len(re.findall(r"Ft\s*/\s*h[oó]", html, re.IGNORECASE))
    print(f"'Ft/hó' occurrences: {ft_count}")
    for m in list(re.finditer(r"Ft\s*/\s*h[oó]", html, re.IGNORECASE))[:2]:
        start = max(0, m.start() - 500)
        end = min(len(html), m.end() + 100)
        print("--- context ---")
        print(html[start:end].replace("\n", " "))

    hrefs = re.findall(r'href="([^"]*kiado-alberlet[^"]*)"', html, re.IGNORECASE)
    print(f"kiado-alberlet hrefs: {len(hrefs)}; sample: {hrefs[:10]}")


if __name__ == "__main__":
    main()
