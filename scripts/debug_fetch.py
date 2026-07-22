#!/usr/bin/env python3
"""One-off diagnostic: dump raw HTML around a listing card on
albifigyelo.hu's Budapest page, to get exact card container structure
for the production scraper. Not part of the regular tracker run."""

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}


def main():
    resp = requests.get("https://albifigyelo.hu/kiado-alberletek/budapest", headers=HEADERS, timeout=20)
    html = resp.text
    print(f"status: {resp.status_code}; length: {len(html)}")

    idx = html.find("/hirdetesek/")
    if idx == -1:
        print("no hirdetesek href found")
        return
    # Back up to the start of the enclosing card-ish container.
    start = max(0, idx - 1500)
    end = min(len(html), idx + 500)
    print("--- raw HTML around first listing href ---")
    print(html[start:end])


if __name__ == "__main__":
    main()
