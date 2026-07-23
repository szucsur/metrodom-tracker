import emailer
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
        furnished_status="full",
        notes=["district-level match only"],
    )
    defaults.update(overrides)
    return Listing(**defaults)


def test_format_email_body_includes_key_fields():
    body = emailer.format_email_body([make_listing()])
    assert "Vágóhíd utca Metrodom Green" in body
    assert "test" in body
    assert "250 000 Ft/hó" in body
    assert "45" in body
    assert "https://example.com/1" in body
    assert "district-level match only" in body


def test_send_email_without_credentials_does_not_raise(monkeypatch, capsys):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    result = emailer.send_email([make_listing()])
    assert result is False
    captured = capsys.readouterr()
    assert "skipping send" in captured.out
