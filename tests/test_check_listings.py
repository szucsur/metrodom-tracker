"""check_listings.py's --test-email mode: sends one synthetic listing to
verify SMTP delivery and the notification template, without touching
scraping, filtering, or dedup state.
"""

import check_listings
import filters


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
