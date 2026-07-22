#!/usr/bin/env python3
"""One-off diagnostic: confirm whether rentingo.com's 403 is a genuine
Cloudflare JS-challenge (unbeatable without a real browser) or just a
simple incomplete-header block, by inspecting the response body and
trying a fuller browser-like header set. Not part of the regular
tracker run."""

import requests

CANDIDATES = [
    {
        "label": "minimal headers",
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        },
    },
    {
        "label": "fuller browser-like headers",
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "sec-ch-ua": '"Chromium";v="124", "Not(A:Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        },
    },
]


def main():
    for candidate in CANDIDATES:
        print("=" * 70)
        print(f"Trying: {candidate['label']}")
        try:
            resp = requests.get("https://rentingo.com/", headers=candidate["headers"], timeout=20)
        except requests.RequestException as exc:
            print(f"  request failed: {exc}")
            continue
        print(f"  status: {resp.status_code}")
        print(f"  server: {resp.headers.get('server')!r}  cf-ray: {resp.headers.get('cf-ray')!r}")
        print(f"  body (first 800 chars): {resp.text[:800]}")


if __name__ == "__main__":
    main()
