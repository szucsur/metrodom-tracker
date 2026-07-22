#!/usr/bin/env python3
"""One-off diagnostic: complete the alberlet.hu search — click #location,
select 'IX. kerület' from the picker, set min-size/min-room, then find
and click the actual submit button, and report the resulting URL + page
content. Diagnostic only, not part of the regular tracker run."""

import re

from playwright.sync_api import sync_playwright

HOME_URL = "https://www.alberlet.hu/"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ))
        page.goto(HOME_URL, wait_until="networkidle", timeout=30000)

        for text in ["Elfogadom", "Rendben", "Accept"]:
            try:
                btn = page.get_by_text(text, exact=False).first
                if btn.is_visible(timeout=1000):
                    btn.click(timeout=1000)
                    page.wait_for_timeout(500)
                    break
            except Exception:
                pass

        page.locator("#location").click(force=True)
        page.wait_for_timeout(800)
        page.get_by_text("IX. kerület", exact=True).first.click(timeout=3000)
        page.wait_for_timeout(500)

        try:
            page.fill("#min-size", "40", timeout=3000)
        except Exception as e:
            print(f"min-size fill failed: {e}")
        try:
            page.fill("#min-room", "2", timeout=3000)
        except Exception as e:
            print(f"min-room fill failed: {e}")

        # Dump all visible clickable buttons/links now, to find the real submit control.
        clickable = page.eval_on_selector_all(
            "button, a, input[type=submit], [role=button]",
            """els => els.filter(e => e.offsetParent !== null).map(e => ({
                tag: e.tagName, text: (e.textContent||'').trim().slice(0,40),
                cls: e.className, href: e.getAttribute('href')
            })).filter(e => e.text.length > 0)"""
        )
        print(f"visible clickable elements ({len(clickable)}):")
        for c in clickable[:40]:
            print(f"  {c}")

        search_click_texts = ["Keresés", "Keresek", "Mutasd", "Találatok", "Ingatlanok"]
        clicked = False
        for t in search_click_texts:
            try:
                el = page.get_by_text(t, exact=False).first
                if el.is_visible(timeout=500):
                    el.click(timeout=2000)
                    print(f"clicked control with text containing {t!r}")
                    clicked = True
                    break
            except Exception:
                continue
        print(f"submit clicked: {clicked}")

        page.wait_for_timeout(3000)
        print(f"=== URL after submit attempt: {page.url}")

        visible_text = page.inner_text("body")
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        ft_count = len(re.findall(r"Ft", visible_text))
        print(f"visible text length: {len(visible_text)}; 'Ft' occurrences: {ft_count}")
        print(f"visible text sample: {visible_text[:2000]}")

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        listing_hrefs = [h for h in hrefs if h and re.search(r"/\d{4,}", h)]
        print(f"total <a href>: {len(hrefs)}; numeric-id-looking: {len(listing_hrefs)}")
        print(f"sample: {listing_hrefs[:15]}")

        browser.close()


if __name__ == "__main__":
    main()
