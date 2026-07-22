#!/usr/bin/env python3
"""One-off diagnostic: render alberlet.hu with a real browser (Playwright)
and report what actually shows up, since the plain-HTTP fetch returned a
page with no visible listing content. Not part of the regular tracker run."""

import re

from playwright.sync_api import sync_playwright

URL = "https://www.alberlet.hu/kiado-lakas/budapest-ix-kerulet"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ))
        page.goto(URL, wait_until="networkidle", timeout=30000)
        # Give any lazy-loaded content a moment past networkidle.
        page.wait_for_timeout(2000)

        html = page.content()
        print(f"rendered HTML length: {len(html)}")

        visible_text = page.inner_text("body")
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        print(f"visible text length: {len(visible_text)}")
        print(f"visible text sample (first 1500 chars): {visible_text[:1500]}")

        ft_count = len(re.findall(r"Ft", visible_text))
        print(f"'Ft' occurrences in visible text: {ft_count}")
        for m in list(re.finditer(r".{80}Ft.{40}", visible_text))[:5]:
            print(f"  context: {m.group(0)}")

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        listing_hrefs = [h for h in hrefs if h and re.search(r"/\d{4,}", h)]
        print(f"total <a href> count: {len(hrefs)}; numeric-id-looking hrefs: {len(listing_hrefs)}")
        print(f"sample listing-looking hrefs: {listing_hrefs[:10]}")

        # Common card container class name candidates, count how many elements match.
        for sel in [".listing", ".list-item", ".property", ".card", "article",
                    "[class*='listing']", "[class*='result']", "[class*='item']"]:
            count = page.eval_on_selector_all(sel, "els => els.length")
            if count:
                print(f"selector {sel!r}: {count} element(s)")

        browser.close()


if __name__ == "__main__":
    main()
