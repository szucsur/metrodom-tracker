"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

First-pass recon of tappancsosotthon.hu — the name ("pawed home" in
Hungarian) doesn't read like a real-estate site, so confirm what this
domain actually is before building anything against it.
"""

import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8",
}

CANDIDATE_URLS = [
    "https://www.tappancsosotthon.hu/",
    "https://tappancsosotthon.hu/",
]


def dump(url):
    print("=" * 80)
    print(f"GET {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"REQUEST FAILED: {exc}")
        return
    print(f"status={resp.status_code} final_url={resp.url}")
    html = resp.text
    print(f"content length: {len(html)}")

    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    print(f"title: {title_match.group(1).strip() if title_match else 'NONE'}")

    desc_match = re.search(r'<meta name="description" content="([^"]*)"', html, re.IGNORECASE)
    print(f"meta description: {desc_match.group(1) if desc_match else 'NONE'}")

    # Sample visible text to see what the site is actually about
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    print(f"visible text sample (first 1000 chars): {text[:1000]}")

    print(f"'kiadó'/'kiado' occurrences: {html.lower().count('kiad')}")
    print(f"'lakás'/'lakas' occurrences: {html.lower().count('lak')}")
    print(f"'kutya' (dog) occurrences: {html.lower().count('kutya')}")
    print(f"'macska' (cat) occurrences: {html.lower().count('macska')}")
    print(f"'örökbefogadás' (adoption) occurrences: {html.lower().count('örökbefogad')}")
    print(f"'menhely' (shelter) occurrences: {html.lower().count('menhely')}")


if __name__ == "__main__":
    for url in CANDIDATE_URLS:
        dump(url)
