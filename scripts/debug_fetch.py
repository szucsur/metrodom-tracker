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
    print(f"  'Ft' occurrences (any context): {len(re.findall('Ft', html))}")
    print(f"  has <noscript>: {'<noscript' in html.lower()}")

    # Signs of a client-side-rendered / API-driven results grid.
    for marker in ["window.__", "algolia", "elasticsearch", "apiUrl", "api.alberlet",
                   "/api/", "graphql", "axios", "fetch(", "data-react", "ng-app", "v-app"]:
        count = html.lower().count(marker.lower())
        if count:
            print(f"  marker {marker!r}: {count} occurrence(s)")

    # Dump script src attributes (external bundles) - helps identify the framework.
    srcs = re.findall(r'<script[^>]+src="([^"]+)"', html, re.IGNORECASE)
    print(f"  script src count: {len(srcs)}; sample: {srcs[:8]}")

    # Dump any inline script tag longer than 200 chars (likely app config/bootstrap data).
    inline_scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.IGNORECASE | re.DOTALL)
    long_inline = [s for s in inline_scripts if len(s.strip()) > 200]
    print(f"  inline <script> blocks: {len(inline_scripts)}, >200 chars: {len(long_inline)}")
    for s in long_inline[:2]:
        print("  --- inline script snippet ---")
        print("  " + s[:500].replace("\n", " "))

    # What's actually in the <body> — first visible text-bearing chunk.
    body_match = re.search(r"<body[^>]*>(.*)", html, re.IGNORECASE | re.DOTALL)
    if body_match:
        body = body_match.group(1)
        text_only = re.sub(r"<[^>]+>", " ", body)
        text_only = re.sub(r"\s+", " ", text_only).strip()
        print(f"  body visible-text length: {len(text_only)}")
        print(f"  body visible-text sample: {text_only[:500]}")


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
