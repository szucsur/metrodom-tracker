#!/usr/bin/env python3
"""One-off diagnostic: actually perform the alberlet.hu search (type a
location into the autocomplete field, set size/room minimums, submit)
and report the resulting URL + page structure, so the real scraper can
be built from ground truth instead of guesses."""

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

        loc = page.locator("#location")
        loc.click()
        loc.fill("")
        loc.type("Budapest IX. ker", delay=80)
        page.wait_for_timeout(1500)

        # Dump whatever dropdown/suggestion elements appeared.
        suggestion_candidates = page.eval_on_selector_all(
            "li, .dropdown-item, [class*='suggest'], [class*='autocomplete'], [role='option']",
            "els => els.filter(e => e.offsetParent !== null).map(e => e.textContent.trim()).filter(t => t.length)"
        )
        print(f"visible suggestion-like texts ({len(suggestion_candidates)}): {suggestion_candidates[:20]}")

        clicked_suggestion = False
        for t in suggestion_candidates:
            if "IX" in t or "Ferencváros" in t or "Ferencvaros" in t:
                try:
                    page.get_by_text(t, exact=True).first.click(timeout=2000)
                    clicked_suggestion = True
                    print(f"clicked suggestion: {t!r}")
                    break
                except Exception as e:
                    print(f"could not click {t!r}: {e}")
        if not clicked_suggestion and suggestion_candidates:
            try:
                page.get_by_text(suggestion_candidates[0], exact=True).first.click(timeout=2000)
                clicked_suggestion = True
                print(f"clicked first suggestion fallback: {suggestion_candidates[0]!r}")
            except Exception as e:
                print(f"fallback click failed: {e}")

        try:
            page.fill("#min-size", "40")
        except Exception as e:
            print(f"could not fill min-size: {e}")
        try:
            page.fill("#min-room", "2")
        except Exception as e:
            print(f"could not fill min-room: {e}")

        # Find a submit control near the search form.
        submit_candidates = page.eval_on_selector_all(
            "button, input[type=submit]",
            "els => els.filter(e => e.offsetParent !== null).map(e => ({tag: e.tagName, type: e.getAttribute('type'), text: (e.textContent||'').trim(), cls: e.className}))"
        )
        print(f"visible button-like elements ({len(submit_candidates)}):")
        for b in submit_candidates[:25]:
            print(f"  {b}")

        search_btn = None
        for b in submit_candidates:
            txt = (b.get("text") or "").lower()
            if "keres" in txt:
                search_btn = b
                break
        print(f"chosen search button candidate: {search_btn}")

        if search_btn and search_btn.get("text"):
            try:
                page.get_by_role("button", name=re.compile(re.escape(search_btn["text"]), re.IGNORECASE)).first.click(timeout=3000)
            except Exception as e:
                print(f"click by role failed: {e}; trying get_by_text")
                try:
                    page.get_by_text(search_btn["text"], exact=True).first.click(timeout=3000)
                except Exception as e2:
                    print(f"get_by_text click also failed: {e2}")

        page.wait_for_timeout(3000)
        print(f"=== final URL: {page.url}")

        visible_text = page.inner_text("body")
        visible_text = re.sub(r"\s+", " ", visible_text).strip()
        print(f"visible text length: {len(visible_text)}")
        ft_count = len(re.findall(r"Ft", visible_text))
        print(f"'Ft' occurrences: {ft_count}")
        print(f"visible text sample: {visible_text[:2000]}")

        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
        listing_hrefs = [h for h in hrefs if h and re.search(r"/\d{4,}", h)]
        print(f"total <a href>: {len(hrefs)}; numeric-id-looking: {len(listing_hrefs)}")
        print(f"sample: {listing_hrefs[:15]}")

        browser.close()


if __name__ == "__main__":
    main()
