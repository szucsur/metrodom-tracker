import smtplib
from email import message_from_string
from email.header import decode_header

import config
import emailer
import filters
from models import Listing


def _decoded_subject(raw_message: str) -> str:
    parsed = message_from_string(raw_message)
    parts = decode_header(parsed["Subject"])
    return "".join(
        text.decode(charset or "ascii") if isinstance(text, bytes) else text
        for text, charset in parts
    )


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
    listing = Listing(**defaults)
    filters.enrich_for_display(listing)
    return listing


def test_format_email_body_includes_key_fields():
    body = emailer.format_email_body([make_listing()])
    assert "Vágóhíd utca Metrodom Green" in body
    assert "test" in body
    assert "250 000 Ft / hó" in body
    assert "45 m²" in body
    assert "2" in body
    assert "https://example.com/1" in body
    assert "Teljesen bútorozott" in body


def test_body_is_entirely_hungarian_header_and_labels():
    body = emailer.format_email_body([make_listing()])
    assert "új találat" in body
    assert "Bérleti díj" in body
    assert "Alapterület" in body
    assert "Szobák száma" in body
    assert "Forrás" in body
    # No leftover English field labels from the old template.
    for banned in ("Price:", "Size:", "Rooms:", "Address:", "Furnished:", "Link:", "Source:"):
        assert banned not in body


def test_price_normalized_regardless_of_source_format():
    cases = ["250 000 Ft/hó", "250000 HUF/hónap", "250e Ft"]
    for price_text in cases:
        body = emailer.format_email_body([make_listing(price_text=price_text)])
        assert "250 000 Ft / hó" in body


def test_furnished_translation():
    for status, expected in [("full", "Teljesen bútorozott"), ("partial", "Részben bútorozott"), ("none", "Bútorozatlan")]:
        body = emailer.format_email_body([make_listing(furnished_status=status)])
        assert expected in body


def test_orientation_translation():
    listing = make_listing(description_text="Napfényes, délnyugati fekvésű lakás.")
    body = emailer.format_email_body([listing])
    assert "Délnyugat" in body
    assert "🧭" in body


def test_missing_orientation_and_furnishing_lines_are_omitted_not_blank():
    listing = make_listing(furnished_status=None, description_text="", notes=[])
    body = emailer.format_email_body([listing])
    assert "🧭" not in body
    assert "🛋️" not in body
    # No blank line where an omitted field would have been.
    assert "\n\n" not in body


def test_missing_data_notes_are_never_shown():
    listing = make_listing(notes=[
        "furnished status not stated — verify manually",
        "terrace/balcony not stated — verify manually",
        "move-in date not stated — verify manually",
    ])
    body = emailer.format_email_body([listing])
    assert "not stated" not in body
    assert "ℹ️" not in body


def test_district_level_note_is_translated_and_shown():
    listing = make_listing(notes=[
        "district-level match only (no street name available from this source) — click through to confirm this is actually the right street"
    ])
    body = emailer.format_email_body([listing])
    assert "ℹ️ Megjegyzések" in body
    assert "kerületi szintű egyezés" in body


def test_no_null_none_or_placeholder_values_leak_into_body():
    listing = make_listing(
        furnished_status=None,
        notes=[],
        description_text="",
        address_text="Budapest IX. kerület, Ferencváros",  # no street suffix
    )
    body = emailer.format_email_body([listing])
    for placeholder in ("None", "null", "N/A", "n/a"):
        assert placeholder not in body


def test_send_email_without_credentials_does_not_raise(monkeypatch, capsys):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    result = emailer.send_email([make_listing()])
    assert result is False
    captured = capsys.readouterr()
    assert "skipping send" in captured.out


class _FakeSMTP:
    sent = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, address, password):
        pass

    def sendmail(self, from_addr, to_addrs, message):
        _FakeSMTP.sent.append((from_addr, list(to_addrs), message))


def test_send_email_delivers_to_every_configured_recipient(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "sender@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password")
    monkeypatch.setattr(config, "EMAIL_TO", ["a@example.com", "b@example.com"])
    _FakeSMTP.sent = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSMTP)

    result = emailer.send_email([make_listing()])
    assert result is True

    from_addr, to_addrs, message = _FakeSMTP.sent[0]
    assert to_addrs == ["a@example.com", "b@example.com"]
    parsed = message_from_string(message)
    assert parsed["To"] == "a@example.com, b@example.com"


def test_send_email_subject_is_fixed_hungarian_format_independent_of_project(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "sender@example.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "app-password")
    monkeypatch.setattr(config, "EMAIL_TO", ["a@example.com"])
    _FakeSMTP.sent = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSMTP)

    for count, expected in [(1, "🏡 Lakásfigyelő: 1 új találat"), (4, "🏡 Lakásfigyelő: 4 új találat"), (12, "🏡 Lakásfigyelő: 12 új találat")]:
        listings = [make_listing(listing_id=str(i)) for i in range(count)]
        emailer.send_email(listings)
        _, _, message = _FakeSMTP.sent[-1]
        subject = _decoded_subject(message)
        assert subject == expected
        assert config.SEARCH_DISPLAY_NAME not in subject
