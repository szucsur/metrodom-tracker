"""Sends the match notification email over SMTP.

Reads credentials from environment variables so no secret ever needs to
be written to disk or committed:

  GMAIL_ADDRESS       - the Gmail account to send from
  GMAIL_APP_PASSWORD  - a Gmail App Password (not the account password;
                        requires 2FA enabled on the account, generated at
                        https://myaccount.google.com/apppasswords)

In GitHub Actions these are read from repository secrets of the same
name (see .github/workflows/metrodom-green-tracker.yml).

The email body is entirely in Hungarian (the recipient's language) and
only ever shows fields that actually have a value — see
_format_listing_block() for the per-field logic. This module only
formats and translates; it never derives new information about a
listing (that's filters.enrich_for_display(), called once per listing
before send_email()) and never changes which listings get emailed.
"""

import os
import smtplib
from email.mime.text import MIMEText

import config
import filters

_SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

_FURNISHED_HU = {
    "full": "Teljesen bútorozott",
    "partial": "Részben bútorozott",
    "none": "Bútorozatlan",
}

_ORIENTATION_HU = {
    "north": "Észak",
    "south": "Dél",
    "east": "Kelet",
    "west": "Nyugat",
    "northeast": "Északkelet",
    "northwest": "Északnyugat",
    "southeast": "Délkelet",
    "southwest": "Délnyugat",
}

# Only filters.py's "district-level match only..." note is genuinely
# useful to a reader (it's a real caveat about match confidence, not a
# missing-data placeholder) — translated here since the email is
# Hungarian-only. The three "X not stated — verify manually" notes are
# intentionally never shown: missing data is just omitted, not called out.
_DISTRICT_LEVEL_NOTE_HU = (
    "Csak kerületi szintű egyezés — ez a forrás nem ad meg utcanevet, "
    "kattints a hirdetésre, hogy megerősítsd, valóban a megfelelő "
    "utcáról van-e szó."
)


def _worthy_notes_hu(listing) -> list:
    notes_hu = []
    for note in listing.notes:
        if "not stated" in note:
            continue
        if note.startswith("district-level match only"):
            notes_hu.append(_DISTRICT_LEVEL_NOTE_HU)
        else:
            notes_hu.append(note)
    return notes_hu


def _format_huf(amount: float) -> str:
    return f"{int(round(amount)):,}".replace(",", " ")


def _format_number_hu(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


def _format_listing_block(listing) -> str:
    lines = []

    name = listing.display_name or listing.title
    if listing.district:
        lines.append(f"📍 {listing.district} • {name}")
    else:
        lines.append(f"📍 {name}")

    price_huf = filters.parse_price_huf(listing.price_text)
    if price_huf is not None:
        lines.append(f"💰 Bérleti díj: {_format_huf(price_huf)} Ft / hó")

    if listing.size_sqm is not None:
        lines.append(f"📐 Alapterület: {_format_number_hu(listing.size_sqm)} m²")

    if listing.rooms is not None:
        lines.append(f"🛏️ Szobák száma: {_format_number_hu(listing.rooms)}")

    if listing.orientation:
        lines.append(f"🧭 Tájolás: {_ORIENTATION_HU.get(listing.orientation, listing.orientation)}")

    if listing.furnished_status:
        lines.append(f"🛋️ Bútorozottság: {_FURNISHED_HU.get(listing.furnished_status, listing.furnished_status)}")

    lines.append(f"🌍 Forrás: {listing.source}")

    if listing.street_address:
        lines.append(f"📍 Cím: {listing.street_address}")

    worthy_notes = _worthy_notes_hu(listing)
    if worthy_notes:
        lines.append("ℹ️ Megjegyzések: " + "; ".join(worthy_notes))

    lines.append(f"🔗 {listing.url}")
    return "\n".join(lines)


def format_email_body(listings) -> str:
    header = f"🔔 {len(listings)} új találat érkezett a(z) „{config.SEARCH_DISPLAY_NAME}” kereséshez"
    parts = [header]
    for listing in listings:
        parts.append(_SEPARATOR)
        parts.append(_format_listing_block(listing))
    return "\n".join(parts)


def send_email(listings, to_address=None) -> bool:
    to_address = to_address or config.EMAIL_TO
    recipients = [to_address] if isinstance(to_address, str) else list(to_address)

    gmail_address = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not app_password:
        print(
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set — skipping send. "
            "Set these as GitHub Actions secrets to enable real email delivery."
        )
        print(format_email_body(listings))
        return False

    subject = f"🏡 Lakásfigyelő: {len(listings)} új találat"
    body = format_email_body(listings)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, recipients, msg.as_string())

    print(f"Sent email with {len(listings)} match(es) to {', '.join(recipients)}")
    return True
