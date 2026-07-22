#!/usr/bin/env python3
"""One-off diagnostic: flatco.hu (WordPress + Easy Property Listings
plugin) — dump the search form's actual option values (district,
bedrooms, price) and then try a constructed search URL to inspect real
listing card markup. Not part of the regular tracker run."""

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


def dump_select_options(soup, name):
    sel = soup.find("select", {"name": name})
    if not sel:
        print(f"  <select name={name!r}> not found")
        return
    print(f"  <select name={name!r}> options:")
    for opt in sel.find_all("option"):
        print(f"    value={opt.get('value')!r} text={opt.get_text(strip=True)!r}")


def dump_checkbox_values(soup, name):
    boxes = soup.find_all("input", {"name": name})
    print(f"  checkboxes name={name!r}:")
    for b in boxes:
        # Find nearby label text.
        label_text = ""
        parent = b.find_parent("label")
        if parent:
            label_text = parent.get_text(strip=True)
        print(f"    value={b.get('value')!r} label={label_text!r}")


def main():
    session = requests.Session()
    resp = session.get("https://flatco.hu/", headers=HEADERS, timeout=20)
    print(f"homepage status: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")

    print("=== district select ===")
    dump_select_options(soup, "district")
    print("=== property_category select/options if any ===")
    dump_select_options(soup, "property_category")
    print("=== property_bedrooms checkboxes ===")
    dump_checkbox_values(soup, "property_bedrooms[]")
    print("=== price from select ===")
    dump_select_options(soup, "property_price_global_from")

    # Now try a constructed search URL using the rental+Apartment link we
    # already found, plus a guessed district param, and see what happens.
    search_url = "https://flatco.hu/"
    params = {
        "action": "epl_search",
        "post_type": "rental",
        "property_status": "current",
        "property_category": "Apartment",
        "lang": "hu",
    }
    print("=" * 70)
    print(f"Trying base rental search: {params}")
    resp2 = session.get(search_url, headers=HEADERS, params=params, timeout=20)
    print(f"status: {resp2.status_code}; final url: {resp2.url}; length: {len(resp2.text)}")
    ft_count = len(re.findall(r"Ft", resp2.text))
    print(f"'Ft' occurrences: {ft_count}")

    soup2 = BeautifulSoup(resp2.text, "html.parser")
    hrefs = [a["href"] for a in soup2.find_all("a", href=True)]
    listing_like = [h for h in hrefs if re.search(r"/ingatlan/|/property/|/listing/", h, re.IGNORECASE)]
    print(f"total hrefs: {len(hrefs)}; listing-like: {len(listing_like)}")
    print(f"sample listing-like hrefs: {listing_like[:10]}")

    # Dump a chunk of visible text to see the repeating listing pattern.
    body = soup2.find("body")
    if body:
        text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
        print(f"body text sample (2000 chars): {text[:2000]}")


if __name__ == "__main__":
    main()
