#!/usr/bin/env python3
"""One-off diagnostic: inspect rentola.hu's dedicated Budapest apartment
listing page structure (status, listing count, card markup for
price/size/rooms/address). Not part of the regular tracker run."""

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
    resp = requests.get("https://rentola.hu/kiado/lakasok/budapest", headers=HEADERS, timeout=20)
    html = resp.text
    print(f"status: {resp.status_code}; length: {len(html)}")

    hrefs = sorted(set(re.findall(r'href="(/listings/[^"]+)"', html)))
    print(f"unique listing hrefs: {len(hrefs)}")
    print(f"sample: {hrefs[:10]}")

    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if body:
        text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
        print(f"body text length: {len(text)}")
        print(f"body text sample (2500 chars): {text[:2500]}")

    # Show raw HTML around the first listing card to find exact class names.
    idx = html.find("/listings/")
    if idx != -1:
        start = max(0, idx - 800)
        end = min(len(html), idx + 800)
        print("--- raw HTML around first listing href ---")
        print(html[start:end])


if __name__ == "__main__":
    main()
