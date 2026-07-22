#!/usr/bin/env python3
"""One-off diagnostic: flatco.hu has a dedicated 'Metrodom Green' nav
link (it's Metrodom's own property management site) — find that exact
URL, fetch it, and inspect whether it lists current rental units
directly or links out to a filtered search. Not part of the regular
tracker run."""

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


def main():
    session = requests.Session()
    resp = session.get("https://flatco.hu/", headers=HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")

    print("=== all nav links containing 'Metrodom' ===")
    metrodom_links = []
    for a in soup.find_all("a", href=True):
        if "metrodom" in a.get_text(strip=True).lower():
            print(f"  text={a.get_text(strip=True)!r} href={a['href']!r}")
            metrodom_links.append(a["href"])

    green_url = None
    for href in metrodom_links:
        if "green" in href.lower():
            green_url = href
            break
    if not green_url:
        print("No href containing 'green' found among Metrodom links.")
        return

    print(f"\nFetching Metrodom Green page: {green_url}")
    resp2 = session.get(green_url, headers=HEADERS, timeout=20)
    print(f"status: {resp2.status_code}; length: {len(resp2.text)}")
    ft_count = len(re.findall(r"Ft", resp2.text))
    print(f"'Ft' occurrences: {ft_count}")

    soup2 = BeautifulSoup(resp2.text, "html.parser")
    body = soup2.find("body")
    if body:
        text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
        print(f"body text sample (2500 chars): {text[:2500]}")

    hrefs = [a["href"] for a in soup2.find_all("a", href=True)]
    listing_like = [h for h in hrefs if re.search(r"property|ingatlan|listing|apartman", h, re.IGNORECASE)]
    print(f"\ntotal hrefs: {len(hrefs)}; property/listing-like: {len(listing_like)}")
    for h in listing_like[:20]:
        print(f"  {h}")


if __name__ == "__main__":
    main()
