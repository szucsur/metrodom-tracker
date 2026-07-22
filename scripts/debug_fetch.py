#!/usr/bin/env python3
"""One-off diagnostic: inspect rentingo.com's real structure — homepage,
whether it's behind Cloudflare/similar bot protection, and its search
form fields, so a real scraper can be built from ground truth. Not part
of the regular tracker run."""

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

CANDIDATES = [
    "https://rentingo.com/",
    "https://www.rentingo.com/",
]


def main():
    session = requests.Session()
    html = None
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
        server = resp.headers.get("server", "")
        cf_ray = resp.headers.get("cf-ray", "")
        print(f"  server header: {server!r}  cf-ray: {cf_ray!r}")
        print(f"  length: {len(resp.text)}")
        if resp.status_code == 200 and html is None:
            html = resp.text

    if not html:
        print("No successful homepage fetch — stopping here.")
        return

    print("=" * 70)
    print("Inspecting homepage content")
    print(f"has __NEXT_DATA__: {'__NEXT_DATA__' in html}")
    print(f"has algolia marker: {'algolia' in html.lower()}")
    print(f"has <noscript>: {'<noscript' in html.lower()}")

    soup = BeautifulSoup(html, "html.parser")

    print("=== forms ===")
    for f in soup.find_all("form"):
        print(f"  form action={f.get('action')!r} method={f.get('method')!r} id={f.get('id')!r} class={f.get('class')!r}")

    print("=== inputs/selects ===")
    for el in soup.find_all(["input", "select"]):
        print(f"  {el.name} type={el.get('type')!r} name={el.get('name')!r} id={el.get('id')!r} "
              f"placeholder={el.get('placeholder')!r} class={el.get('class')!r}")

    print("=== nav/menu links possibly related to search/kiado/rent ===")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if re.search(r"kiad|berlet|kereses|search|lakas|rent|apartment", href, re.IGNORECASE) or \
           re.search(r"kiad|berlet|kereses|keres|rent|apartment", text, re.IGNORECASE):
            print(f"  href={href!r} text={text[:40]!r}")


if __name__ == "__main__":
    main()
