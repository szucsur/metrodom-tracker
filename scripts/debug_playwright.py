#!/usr/bin/env python3
"""One-off diagnostic: the #location field on alberlet.hu is readonly, so
clicking it must open a picker overlay with its own input. Find that
input, then complete the search flow. Diagnostic only, not part of the
regular tracker run."""

import re

from playwright.sync_api import sync_playwright

HOME_URL = "https://www.alberlet.hu/"


def dump_visible_inputs(page, label):
    inputs = page.eval_on_selector_all(
        "input, [contenteditable='true']",
        """els => els.filter(e => e.offsetParent !== null).map(e => ({
            tag: e.tagName, type: e.getAttribute('type'), id: e.id,
            name: e.getAttribute('name'), placeholder: e.getAttribute('placeholder'),
            readonly: e.hasAttribute('readonly'), cls: e.className
        }))"""
    )
    print(f"=== visible inputs after {label} ({len(inputs)}) ===")
    for i in inputs[:30]:
        print(f"  {i}")
    return inputs


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

        dump_visible_inputs(page, "page load")

        page.locator("#location").click(force=True)
        page.wait_for_timeout(1000)
        after_click = dump_visible_inputs(page, "clicking #location")

        # Try any newly-visible, non-readonly text input as the real search box.
        real_input = None
        for i in after_click:
            if i.get("tag") == "INPUT" and i.get("type") in (None, "text", "search") and not i.get("readonly"):
                real_input = i
                break
        print(f"chosen real search input: {real_input}")

        if real_input:
            sel = f"#{real_input['id']}" if real_input.get("id") else None
            if sel:
                try:
                    page.fill(sel, "Budapest IX. ker", timeout=5000)
                    page.wait_for_timeout(1500)
                except Exception as e:
                    print(f"fill failed on {sel}: {e}")

        # Whatever suggestion list appears now.
        suggestions = page.eval_on_selector_all(
            "li, .dropdown-item, [class*='suggest'], [class*='autocomplete'], [role='option']",
            "els => els.filter(e => e.offsetParent !== null).map(e => e.textContent.trim()).filter(t => t.length)"
        )
        print(f"visible suggestion-like texts ({len(suggestions)}): {suggestions[:20]}")

        for t in suggestions:
            if "IX" in t or "Ferencváros" in t or "Ferencvaros" in t:
                try:
                    page.get_by_text(t, exact=True).first.click(timeout=2000)
                    print(f"clicked suggestion: {t!r}")
                    break
                except Exception as e:
                    print(f"click failed for {t!r}: {e}")

        page.wait_for_timeout(1000)
        dump_visible_inputs(page, "selecting a suggestion")

        print(f"=== current URL: {page.url}")
        browser.close()


if __name__ == "__main__":
    main()
