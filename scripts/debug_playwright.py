"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

oc.hu's rental list page (/index.php/ingatlanok/lista/ertekesites:kiado) is
built with Symfony UX Live Components: plain query-string params on the URL
don't change the result set (total count stayed 6548 regardless). This
drives the real search form in a headless browser, captures every
XHR/fetch/document request fired when the form is submitted, and prints the
one(s) that look like they carry search results — so we can hit that same
endpoint directly with `requests` in production, without needing a browser
at runtime.
"""

from playwright.sync_api import sync_playwright

LIST_URL = "https://www.oc.hu/index.php/ingatlanok/lista/ertekesites:kiado"


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        requests_seen = []

        def on_request(req):
            if req.resource_type in ("xhr", "fetch", "document"):
                requests_seen.append((req.method, req.url, req.post_data))

        page.on("request", on_request)

        page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
        print(f"Initial load requests captured: {len(requests_seen)}")

        # Try to find and fill the room-count / size filter, then submit.
        try:
            page.fill("#realestate_szoba_min", "2")
        except Exception as exc:
            print(f"could not fill szoba_min: {exc}")
        try:
            page.fill("#realestate_meretNetto_min", "40")
        except Exception as exc:
            print(f"could not fill meretNetto_min: {exc}")

        requests_seen.clear()

        # Look for a submit/search button
        submit_selectors = [
            "button[type=submit]",
            "button:has-text('Keresés')",
            "button:has-text('Keres')",
        ]
        clicked = False
        for sel in submit_selectors:
            try:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    clicked = True
                    print(f"clicked selector: {sel}")
                    break
            except Exception as exc:
                print(f"selector {sel} failed: {exc}")
        if not clicked:
            print("no submit button matched — trying Enter key on last focused field")
            try:
                page.keyboard.press("Enter")
            except Exception as exc:
                print(f"Enter press failed: {exc}")

        page.wait_for_timeout(4000)

        print(f"Requests after submit: {len(requests_seen)}")
        for method, url, post_data in requests_seen:
            print(f"  {method} {url}")
            if post_data:
                print(f"    post_data: {post_data[:500]}")

        print("Final page URL:", page.url)
        content_len = len(page.content())
        print("Final page content length:", content_len)

        browser.close()


if __name__ == "__main__":
    run()
