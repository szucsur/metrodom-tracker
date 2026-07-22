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
    "https://ingatlan.com/lista/kiado+lakas+budapest-ix-ker",
    "https://ingatlan.com/szukites/kiado+lakas+budapest-ix-ker",
    "https://ingatlan.com/",
    "https://www.alberlet.hu/",
    "https://www.alberlet.hu/kiado-lakas",
    "https://www.alberlet.hu/kiado-lakas/budapest",
    "https://www.alberlet.hu/kiado-lakas/budapest-ix-kerulet",
    "https://alberlet.hu/kiado-lakas/budapest-ix-kerulet",
]


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
        server = resp.headers.get("server", "")
        cf_ray = resp.headers.get("cf-ray", "")
        print(f"  server header: {server!r}  cf-ray: {cf_ray!r}")
        snippet = resp.text[:600].replace("\n", " ")
        print(f"  body snippet: {snippet}")
        has_next_data = "__NEXT_DATA__" in resp.text
        print(f"  has __NEXT_DATA__: {has_next_data}")


if __name__ == "__main__":
    main()
