#!/usr/bin/env python3
"""One-off diagnostic: fetch a flatco.hu rental unit detail page
(the live nav exposes each currently-available unit as a direct link,
e.g. 'Metrodom Green - A.B.304' -> /rental/metrodom-green-a-b-304/) and
inspect what data it contains: price, size, rooms, furnished, terrace,
move-in date. Not part of the regular tracker run."""

import re

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

URL = "https://flatco.hu/rental/metrodom-green-a-b-304/"


def main():
    session = requests.Session()
    resp = session.get(URL, headers=HEADERS, timeout=20)
    print(f"status: {resp.status_code}; length: {len(resp.text)}")
    html = resp.text

    print(f"'Ft' occurrences: {len(re.findall('Ft', html))}")
    print(f"'m2' or m² occurrences: {len(re.findall('m2|m²', html))}")
    print(f"'szoba' occurrences: {len(re.findall('szoba', html, re.IGNORECASE))}")
    print(f"has __NEXT_DATA__: {'__NEXT_DATA__' in html}")

    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if body:
        text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
        print(f"body text length: {len(text)}")
        print(f"body text sample (3000 chars): {text[:3000]}")

    # Also list all currently-available unit links found anywhere on this page's nav.
    print("\n=== 'Metrodom Green - X' style links on this page ===")
    for a in soup.find_all("a", href=True):
        t = a.get_text(strip=True)
        if re.match(r"^[A-Za-zÀ-ÿ0-9 .]+ - [A-Za-z0-9.]+$", t):
            print(f"  text={t!r} href={a['href']!r}")


if __name__ == "__main__":
    main()
