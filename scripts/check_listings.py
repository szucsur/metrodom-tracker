#!/usr/bin/env python3
"""Main entry point: fetch, filter, dedup, and email new rental matches.

Usage:
    python check_listings.py                  # normal run: emails new matches
    python check_listings.py --dry-run        # print what would be sent, no email, no state write
    python check_listings.py --test-email     # send one synthetic listing to verify email delivery/template
    python check_listings.py --send-all-matches  # email every currently matching listing, ignoring dedup state
"""

import argparse
import sys

import filters
from emailer import send_email
from models import Listing
from scrapers import (
    ingatlan,
    alberlet,
    facebook,
    flatco,
    rentingo,
    albifigyelo,
    rentola,
    oc,
    megveszlak,
    tappancsosotthon,
    maxapro,
    koltozzbe,
)
from state import load_seen, save_seen


def build_test_listing() -> Listing:
    """A synthetic, clearly-labeled listing used only by --test-email to
    verify SMTP delivery and the notification template — never touches
    scraping, filtering, dedup state, or any real source."""
    return Listing(
        source="teszt",
        listing_id="test-email",
        url="https://example.com/teszt-hirdetes",
        title="TESZT üzenet — Metrodom Green",
        price_text="280 000 Ft/hó",
        size_sqm=45.0,
        rooms=2.0,
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text=(
            "Ez egy teszt hirdetés a lakáskereső email-sablonjának "
            "ellenőrzésére. Teljesen bútorozott, déli fekvésű, azonnal "
            "költözhető."
        ),
    )


def gather_all_listings():
    listings = []
    for scraper in (
        ingatlan,
        alberlet,
        facebook,
        flatco,
        rentingo,
        albifigyelo,
        rentola,
        oc,
        megveszlak,
        tappancsosotthon,
        maxapro,
        koltozzbe,
    ):
        try:
            found = scraper.fetch()
            print(f"[{scraper.__name__}] fetched {len(found)} listing(s)")
            listings.extend(found)
        except Exception as exc:  # keep one source's failure from killing the run
            print(f"[{scraper.__name__}] unexpected error: {exc}")
    return listings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't send email or update dedup state")
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send one synthetic test listing to verify delivery/template, bypassing scraping/filtering/dedup",
    )
    parser.add_argument(
        "--send-all-matches",
        action="store_true",
        help="Scrape and filter for real, then email every currently matching listing "
        "(not just ones new since the last run) — ignores and does not update dedup state",
    )
    args = parser.parse_args()

    if args.test_email:
        listing = build_test_listing()
        filters.annotate(listing)
        filters.enrich_for_display(listing)
        send_email([listing])
        return 0

    all_listings = gather_all_listings()
    matches = filters.apply_all(all_listings)
    print(f"{len(matches)} listing(s) pass the Metrodom Green filters")
    for m in matches:
        print(f"  match: [{m.source}] {m.title} -> {m.url}")

    if args.send_all_matches:
        if not matches:
            print("No current matches — no email sent.")
            return 0
        for m in matches:
            filters.enrich_for_display(m)
        send_email(matches)
        return 0

    seen = load_seen()
    new_matches = [m for m in matches if m.dedup_key() not in seen]
    print(f"{len(new_matches)} of those are new since the last run")

    if not new_matches:
        print("Nothing new — no email sent.")
        return 0

    for m in new_matches:
        print(f"NEW MATCH: [{m.source}] {m.title} -> {m.url}")

    if args.dry_run:
        print("--dry-run set: not sending email or updating state.")
        return 0

    for m in new_matches:
        filters.enrich_for_display(m)
    send_email(new_matches)

    seen.update(m.dedup_key() for m in new_matches)
    save_seen(seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
