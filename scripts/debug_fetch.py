#!/usr/bin/env python3
"""One-off diagnostic: inspect albifigyelo.hu's Budapest listing page
(for filter options / query params) and a single listing detail page
(for full address/price/size/room/description fields). Not part of the
regular tracker run."""

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


def dump_page(session, url, label):
    print("=" * 70)
    print(f"{label}: {url}")
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as exc:
        print(f"  request failed: {exc}")
        return None
    print(f"  status: {resp.status_code}; length: {len(resp.text)}")
    return resp.text


def main():
    session = requests.Session()

    html = dump_page(session, "https://albifigyelo.hu/kiado-alberletek/budapest", "Budapest listing page")
    if html:
        soup = BeautifulSoup(html, "html.parser")
        print("=== forms ===")
        for f in soup.find_all("form"):
            print(f"  form action={f.get('action')!r} method={f.get('method')!r}")
        print("=== inputs/selects ===")
        for el in soup.find_all(["input", "select"]):
            print(f"  {el.name} type={el.get('type')!r} name={el.get('name')!r} id={el.get('id')!r} "
                  f"placeholder={el.get('placeholder')!r}")
        body = soup.find("body")
        if body:
            text = re.sub(r"\s+", " ", body.get_text(" ", strip=True))
            print(f"body text length: {len(text)}")
            print(f"body text sample (2500 chars): {text[:2500]}")
        hirdetes_hrefs = sorted(set(
            a["href"] for a in soup.find_all("a", href=True) if "/hirdetesek/" in a["href"]
        ))
        print(f"unique listing detail hrefs on this page: {len(hirdetes_hrefs)}")
        print(f"sample: {hirdetes_hrefs[:5]}")

        # Try a district-filtered variant to see if query params narrow results.
        for suffix in ["?kerulet=9", "?district=9", "/ix-kerulet", "?ker=IX"]:
            test_url = "https://albifigyelo.hu/kiado-alberletek/budapest" + suffix
            resp = session.get(test_url, headers=HEADERS, timeout=20)
            print(f"  district-filter attempt {suffix!r}: status={resp.status_code} length={len(resp.text)}")

    detail_html = dump_page(session, "https://albifigyelo.hu/hirdetesek/58206719", "Sample detail page")
    if detail_html:
        soup2 = BeautifulSoup(detail_html, "html.parser")
        body2 = soup2.find("body")
        if body2:
            text2 = re.sub(r"\s+", " ", body2.get_text(" ", strip=True))
            print(f"detail body text length: {len(text2)}")
            print(f"detail body text sample (2500 chars): {text2[:2500]}")


if __name__ == "__main__":
    main()
