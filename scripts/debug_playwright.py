#!/usr/bin/env python3
"""One-off diagnostic: drive alberlet.hu's own homepage search UI with a
real browser to find the correct search-results URL, since the guessed
URL path turned out to be the site's own "page not found" page (a soft
404 that still returns HTTP 200). Not part of the regular tracker run."""

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

        # Dismiss cookie banner if present.
        for text in ["Elfogadom", "Rendben", "Accept"]:
            try:
                btn = page.get_by_text(text, exact=False).first
                if btn.is_visible(timeout=1000):
                    btn.click(timeout=1000)
                    page.wait_for_timeout(500)
                    break
            except Exception:
                pass

        print("=== forms on homepage ===")
        forms = page.eval_on_selector_all("form", """els => els.map(f => ({
            action: f.getAttribute('action'),
            method: f.getAttribute('method'),
            id: f.id,
            cls: f.className
        }))""")
        for f in forms:
            print(f"  form: {f}")

        print("=== inputs/selects on homepage ===")
        inputs = page.eval_on_selector_all("input, select", """els => els.map(e => ({
            tag: e.tagName,
            type: e.getAttribute('type'),
            name: e.getAttribute('name'),
            id: e.id,
            placeholder: e.getAttribute('placeholder'),
            cls: e.className
        }))""")
        for i in inputs[:40]:
            print(f"  {i}")

        # Try to find a location/search text input and type into it.
        candidates = [i for i in inputs if i.get("tag") == "INPUT" and (
            (i.get("placeholder") or "").lower().find("kerül") >= 0
            or (i.get("placeholder") or "").lower().find("hol") >= 0
            or (i.get("placeholder") or "").lower().find("cím") >= 0
            or (i.get("placeholder") or "").lower().find("keres") >= 0
            or (i.get("name") or "").lower().find("locat") >= 0
            or (i.get("name") or "").lower().find("hely") >= 0
        )]
        print(f"=== candidate location input(s): {candidates}")

        browser.close()


if __name__ == "__main__":
    main()
