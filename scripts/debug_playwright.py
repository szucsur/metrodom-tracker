"""Temporary diagnostic script for GitHub Actions — not part of the tracker.

oc.hu's rental list page (/index.php/ingatlanok/lista/ertekesites:kiado) is
built with Symfony UX Live Components: plain query-string params on the URL
don't change the result set (total count stayed 6548 regardless). This
drives the real search form in a headless browser, captures every
XHR/fetch/document request fired when the form is submitted, and prints the
one(s) that look like they carry search results — so we can hit that same
endpoint directly with `requests` in production, without needing a browser
at runtime.

(Previous attempt crashed: reading req.post_data raised UnicodeDecodeError
for a binary/gzip-encoded request, which broke Playwright's internal event
dispatch loop for the rest of the run. Guarded every access below.)
"""

from playwright.sync_api import sync_playwright

LIST_URL = "https://www.oc.hu/index.php/ingatlanok/lista/ertekesites:kiado"


def describe(req):
    try:
        post_data = req.post_data
    except Exception:
        post_data = "<unreadable>"
    return (req.method, req.url, req.resource_type, post_data)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        requests_seen = []

        def on_request(req):
            try:
                if req.resource_type in ("xhr", "fetch", "document"):
                    requests_seen.append(describe(req))
            except Exception as exc:
                print(f"on_request handler error (ignored): {exc}")

        page.on("request", on_request)

        page.goto(LIST_URL, wait_until="networkidle", timeout=30000)
        print(f"Initial load requests captured: {len(requests_seen)}")
        for method, url, rtype, post_data in requests_seen:
            print(f"  INITIAL {method} {rtype} {url}")
            if post_data and post_data != "<unreadable>":
                print(f"    post_data: {post_data[:500]}")

        requests_seen.clear()

        try:
            page.fill("#realestate_szoba_min", "2")
        except Exception as exc:
            print(f"could not fill szoba_min: {exc}")
        try:
            page.fill("#realestate_meretNetto_min", "40")
        except Exception as exc:
            print(f"could not fill meretNetto_min: {exc}")

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
            print("no submit button matched")

        try:
            page.wait_for_timeout(4000)
        except Exception as exc:
            print(f"wait_for_timeout failed (ignored): {exc}")

        print(f"Requests after submit: {len(requests_seen)}")
        for method, url, rtype, post_data in requests_seen:
            print(f"  AFTER {method} {rtype} {url}")
            if post_data and post_data != "<unreadable>":
                print(f"    post_data: {post_data[:500]}")

        try:
            print("Final page URL:", page.url)
        except Exception as exc:
            print(f"could not read page.url: {exc}")

        browser.close()


if __name__ == "__main__":
    run()
