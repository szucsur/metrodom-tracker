"""Filtering logic shared by all scrapers.

Hard filters (size, rooms, location keyword) drop a listing outright when
the data says it fails. Soft filters (furnished, outdoor space, move-in
date) only drop a listing when the listing text *confirms* it fails; when
the relevant detail simply isn't stated in the search-result text, the
listing is kept and flagged "unconfirmed" so a human can check it rather
than being silently dropped by an imperfect parse.
"""

import re
from datetime import datetime
from typing import Optional

import config
from models import Listing


def text_matches_any(text: str, keywords) -> bool:
    text = (text or "").lower()
    return any(kw in text for kw in keywords)


def location_matches(listing: Listing) -> bool:
    haystack = f"{listing.title} {listing.address_text} {listing.description_text}"
    if text_matches_any(haystack, config.ADDRESS_KEYWORDS):
        return True
    if listing.location_precision == "district":
        # This source never exposes a street name, even in structured
        # data — accept a district-level match, but flag it (see
        # passes_soft_filters) since it isn't confirmed to be the exact
        # street/building.
        return text_matches_any(haystack, config.LOCATION_HINTS)
    return (
        text_matches_any(haystack, config.LOCATION_HINTS)
        and text_matches_any(haystack, ["vágóhíd", "vagohid", "metrodom green"])
    )


def size_ok(listing: Listing) -> bool:
    return listing.size_sqm is not None and listing.size_sqm >= config.MIN_SIZE_SQM


def rooms_ok(listing: Listing) -> bool:
    return listing.rooms is not None and listing.rooms >= config.MIN_ROOMS


# Matches a HUF amount followed by a thousand-forint shorthand, e.g.
# "180e Ft" (oc.hu) or "180 ezer Ft" -> 180 * 1000.
_PRICE_THOUSAND_RE = re.compile(r"(\d[\d\s.,]*)\s*e(?:zer)?\s*(?:ft|huf)\b", re.IGNORECASE)
# Matches a plain HUF amount, e.g. "220 000 Ft/hó" or "220000 HUF/hónap".
_PRICE_PLAIN_RE = re.compile(r"(\d[\d\s.,]*)\s*(?:ft|huf)\b", re.IGNORECASE)
_DIGITS_ONLY_RE = re.compile(r"^[\d\s.,]+$")


def parse_price_huf(price_text: str) -> Optional[float]:
    """Best-effort HUF amount extraction across all sources' price text
    formats. Returns None if the text is empty, is denominated in a
    non-HUF currency, or doesn't contain a recognizable amount."""
    text = (price_text or "").strip()
    if not text:
        return None
    if "€" in text or "eur" in text.lower():
        return None  # not HUF-denominated; can't compare against a HUF cap

    match = _PRICE_THOUSAND_RE.search(text)
    if match:
        digits = re.sub(r"[^\d]", "", match.group(1))
        return float(digits) * 1000 if digits else None

    match = _PRICE_PLAIN_RE.search(text)
    if match:
        digits = re.sub(r"[^\d]", "", match.group(1))
        return float(digits) if digits else None

    if _DIGITS_ONLY_RE.match(text):
        # No currency token at all (e.g. a raw numeric price field) —
        # assume it's already a plain HUF amount.
        digits = re.sub(r"[^\d]", "", text)
        return float(digits) if digits else None

    return None


def price_ok(listing: Listing) -> bool:
    price_huf = parse_price_huf(listing.price_text)
    return price_huf is not None and price_huf <= config.MAX_RENT_HUF


def detect_furnished(text: str) -> Optional[str]:
    text = (text or "").lower()
    # Checked before the plain "furnished" keywords since "bútorozatlan"
    # ("unfurnished") contains "bútor" but is a distinct, opposite claim —
    # order matters here, not just presence.
    if text_matches_any(text, config.UNFURNISHED_KEYWORDS):
        return "none"
    if text_matches_any(text, config.PARTIALLY_FURNISHED_KEYWORDS):
        return "partial"
    if text_matches_any(text, config.FURNISHED_KEYWORDS):
        return "full"
    return None


def detect_outdoor_space(text: str) -> Optional[bool]:
    text = (text or "").lower()
    if text_matches_any(text, config.OUTDOOR_SPACE_KEYWORDS):
        return True
    return None  # not mentioned != confirmed absent


_MOVE_IN_DATE_RE = re.compile(
    r"(\d{4})\.?\s*(" + "|".join(config.HUNGARIAN_MONTHS.keys()) + r")",
    re.IGNORECASE,
)


def detect_move_in_ok(text: str) -> Optional[bool]:
    text = (text or "").lower()
    if text_matches_any(text, config.IMMEDIATE_MOVE_IN_KEYWORDS) or "költözhető" in text or "koltozheto" in text:
        return True
    match = _MOVE_IN_DATE_RE.search(text)
    if match:
        year = int(match.group(1))
        month = config.HUNGARIAN_MONTHS[match.group(2).lower()]
        target = (config.EARLIEST_MOVE_IN_YEAR, config.EARLIEST_MOVE_IN_MONTH)
        return (year, month) >= target
    return None  # not stated, needs a manual check


# Compound directions checked before simple ones, since e.g. "délnyugati"
# contains "nyugati" as a substring — checking simple directions first
# would lose the "south" component and misreport it as plain "west".
_ORIENTATION_KEYWORDS = [
    (["északkeleti", "észak-keleti"], "northeast"),
    (["északnyugati", "észak-nyugati"], "northwest"),
    (["délkeleti", "dél-keleti"], "southeast"),
    (["délnyugati", "dél-nyugati"], "southwest"),
    (["északi"], "north"),
    (["déli"], "south"),
    (["keleti"], "east"),
    (["nyugati"], "west"),
]


def detect_orientation(text: str) -> Optional[str]:
    text = (text or "").lower()
    for keywords, value in _ORIENTATION_KEYWORDS:
        if text_matches_any(text, keywords):
            return value
    return None  # not stated — omitted from display, not shown as unknown


def annotate(listing: Listing) -> Listing:
    combined_text = f"{listing.description_text} {listing.title}"
    listing.furnished_status = detect_furnished(combined_text)
    listing.has_outdoor_space = detect_outdoor_space(combined_text)
    listing.move_in_ok = detect_move_in_ok(combined_text)
    return listing


def passes_hard_filters(listing: Listing) -> bool:
    return (
        location_matches(listing)
        and size_ok(listing)
        and rooms_ok(listing)
        and price_ok(listing)
    )


def passes_soft_filters(listing: Listing) -> bool:
    """Only excludes when a soft criterion is explicitly contradicted."""
    if listing.location_precision == "district":
        listing.notes.append(
            "district-level match only (no street name available from this "
            "source) — click through to confirm this is actually the right street"
        )
    if listing.furnished_status is None:
        listing.notes.append("furnished status not stated — verify manually")
    if listing.has_outdoor_space is None:
        listing.notes.append("terrace/balcony not stated — verify manually")
    elif listing.has_outdoor_space is False:
        return False
    if listing.move_in_ok is None:
        listing.notes.append("move-in date not stated — verify manually")
    elif listing.move_in_ok is False:
        return False
    return True


def is_fresh(listing: Listing, now: Optional[datetime] = None) -> bool:
    if not listing.posted_at:
        return True  # can't tell, let the dedup state file be the gate
    now = now or datetime.utcnow()
    try:
        posted = datetime.fromisoformat(listing.posted_at)
    except ValueError:
        return True
    age_minutes = (now - posted).total_seconds() / 60
    return age_minutes <= config.FRESHNESS_WINDOW_MINUTES


def apply_all(listings):
    matches = []
    for listing in listings:
        annotate(listing)
        if passes_hard_filters(listing) and passes_soft_filters(listing):
            matches.append(listing)
    return matches


# --- Display-only enrichment ------------------------------------------------
#
# Everything below derives extra fields (district, a real street address,
# orientation) for the email template. None of it runs as part of
# apply_all() and none of it can change which listings pass filtering,
# how they're deduped, or how they're ranked/ordered — it's called
# separately, only on listings that have already been selected as new
# matches, purely to make the notification nicer. See emailer.py.

_VALID_BUDAPEST_DISTRICTS = {
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    "XXI", "XXII", "XXIII",
}

# Anchored to the start of the text: sources like tappancsosotthon.hu
# title their listings "IV. Metrodom Panoráma" / "VII. Csányi utca" —
# district prefix, then the actual building/street name.
_LEADING_DISTRICT_RE = re.compile(r"^([IVXLCM]+)\.\s+(.+)$")
# Unanchored: general "... Budapest, IX. kerület" style mentions anywhere
# in address/description text.
_DISTRICT_MENTION_RE = re.compile(r"\b([IVXLCM]+)\.\s*ker(?:ület)?\b", re.IGNORECASE)

# Deliberately conservative — words that are unambiguously a street/square
# type in Hungarian, not neighborhood or development names (which can
# coincidentally end in similar-sounding words). Under-detecting a real
# address is preferable to mislabeling a neighborhood/project name as a
# street and repeating it as if it were new information.
_STREET_SUFFIX_RE = re.compile(
    r"\b(utca|út|körút|tér|sétány|köz|dűlő|fasor|rakpart)\b", re.IGNORECASE
)


def _looks_like_street_address(text: str) -> bool:
    return bool(_STREET_SUFFIX_RE.search(text or ""))


def compute_display_fields(listing: Listing) -> dict:
    """Derive (district, name, street_address) for the email template from
    already-parsed listing text. Pure function — makes no assumptions
    beyond what the listing already carries, and never fabricates a value
    it can't support with text actually present on the listing.

    street_address is deliberately suppressed (set to None) whenever it
    would just repeat text already shown in the headline (district +
    name) — e.g. tappancsosotthon.hu's "VII. Csányi utca" already puts
    the street name in the headline via the leading-district split, and
    alberlet.hu's headline already leads with the street name too, so a
    separate "Cím: Csányi utca" / "Cím: Vágóhíd utca" line underneath
    would add no new information, only repeat it. This favors never
    repeating information over always showing an address line."""
    title = (listing.title or "").strip()

    leading_match = _LEADING_DISTRICT_RE.match(title)
    if leading_match and leading_match.group(1) in _VALID_BUDAPEST_DISTRICTS:
        district = f"{leading_match.group(1)}. kerület"
        name = leading_match.group(2).strip()
    else:
        name = title or listing.address_text.strip() or "Ismeretlen ingatlan"
        district = None
        mention = _DISTRICT_MENTION_RE.search(
            f"{title} {listing.address_text} {listing.description_text}"
        )
        if mention and mention.group(1).upper() in _VALID_BUDAPEST_DISTRICTS:
            district = f"{mention.group(1).upper()}. kerület"

    street_address = None
    if _looks_like_street_address(listing.address_text or ""):
        # Isolate the street portion from formats like "Vágóhíd utca
        # Budapest, IX. kerület" — take whatever precedes the district/city
        # mention rather than showing the whole blob.
        candidate = re.split(r"\bBudapest\b|,", listing.address_text, maxsplit=1)[0].strip()
        street_address = candidate or None
    elif _looks_like_street_address(name):
        street_address = name

    if street_address and (
        street_address.lower() in name.lower()
        or (district and street_address.lower() == district.lower())
    ):
        street_address = None

    return {"district": district, "name": name, "street_address": street_address}


def enrich_for_display(listing: Listing) -> Listing:
    """Populates district/street_address/orientation for one listing,
    right before it's emailed. Safe to call multiple times; never touches
    anything used by filtering, matching, or dedup."""
    fields = compute_display_fields(listing)
    listing.district = fields["district"]
    listing.display_name = fields["name"]
    listing.street_address = fields["street_address"]
    combined_text = f"{listing.description_text} {listing.title}"
    listing.orientation = detect_orientation(combined_text)
    return listing
