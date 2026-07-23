"""check_listings.py's --test-email mode: sends one synthetic listing to
verify SMTP delivery and the notification template, without touching
scraping, filtering, or dedup state.
"""

import check_listings
import filters
from models import Listing


def make_listing(**overrides):
    defaults = dict(
        source="test",
        listing_id="1",
        url="https://example.com/1",
        title="Vágóhíd utca Metrodom Green",
        price_text="250 000 Ft/hó",
        size_sqm=45,
        rooms=2,
        address_text="Vágóhíd utca Budapest, IX. kerület",
    )
    defaults.update(overrides)
    return Listing(**defaults)


def test_build_test_listing_passes_hard_filters():
    # The synthetic listing should look like a genuine Metrodom Green
    # match so it exercises the real template exactly as a live match
    # would — a --test-email that silently failed the filters it's meant
    # to simulate would be a misleading test.
    listing = check_listings.build_test_listing()
    filters.annotate(listing)
    assert filters.passes_hard_filters(listing)
    assert filters.passes_soft_filters(listing)


def test_test_email_mode_never_touches_scraping_or_state(monkeypatch, capsys):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    def _fail_if_called():
        raise AssertionError("--test-email must not call gather_all_listings()")

    monkeypatch.setattr(check_listings, "gather_all_listings", _fail_if_called)
    monkeypatch.setattr("sys.argv", ["check_listings.py", "--test-email"])

    exit_code = check_listings.main()
    assert exit_code == 0

    body = capsys.readouterr().out
    assert "TESZT" in body
    assert "🔔" in body


def test_send_all_matches_emails_every_match_and_ignores_seen_state(monkeypatch, capsys):
    already_seen = make_listing(listing_id="already-seen")
    brand_new = make_listing(listing_id="brand-new")

    monkeypatch.setattr(check_listings, "gather_all_listings", lambda: [already_seen, brand_new])
    monkeypatch.setattr(check_listings, "load_seen", lambda: {already_seen.dedup_key()})

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("--send-all-matches must not write dedup state")

    monkeypatch.setattr(check_listings, "save_seen", _fail_if_called)

    sent = {}

    def _fake_send_email(listings):
        sent["listings"] = listings
        return True

    monkeypatch.setattr(check_listings, "send_email", _fake_send_email)
    monkeypatch.setattr("sys.argv", ["check_listings.py", "--send-all-matches"])

    exit_code = check_listings.main()
    assert exit_code == 0
    assert {m.listing_id for m in sent["listings"]} == {"already-seen", "brand-new"}


def test_send_all_matches_sends_nothing_when_no_current_matches(monkeypatch, capsys):
    monkeypatch.setattr(check_listings, "gather_all_listings", lambda: [])

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("send_email must not be called when there are no matches")

    monkeypatch.setattr(check_listings, "send_email", _fail_if_called)
    monkeypatch.setattr("sys.argv", ["check_listings.py", "--send-all-matches"])

    exit_code = check_listings.main()
    assert exit_code == 0
    assert "No current matches" in capsys.readouterr().out
