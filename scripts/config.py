"""Search configuration for the rental listing tracker.

Edit this file to point the tracker at a different building, area, or
filter set. Defaults below are tuned for the Metrodom Green complex.
"""

# Text that must appear (case-insensitive) in a listing's address/title/
# description for it to be considered a match. A listing matches if ANY
# of these strings is found.
ADDRESS_KEYWORDS = [
    "vágóhíd",
    "vagohid",
    "metrodom green",
    "cordia woodland",
]
# Deliberately NOT including bare "metrodom" or bare "cordia" here: several
# other buildings share each brand (Metrodom River/Park/Panoráma/City
# Home/etc.; Cordia develops many unrelated projects across Budapest), and
# a loose brand-only match would short-circuit location_matches() into
# treating any of them as a target building — this bit us for real once a
# source (tappancsosotthon.hu) listed multiple Metrodom buildings at once.
# The specific complex name ("metrodom green", "cordia woodland") is
# enough, and is what location_matches() actually needs.

# Budapest postal code / district hints used as a secondary signal when a
# listing doesn't spell out the street name.
LOCATION_HINTS = ["1097", "ix. ker", "ix.ker", "budapest ix"]

MIN_SIZE_SQM = 40
MIN_ROOMS = 2

# Hard cap on monthly rent, in HUF. A listing whose price can't be parsed
# from its source text is treated as failing this filter (never shown),
# not "unconfirmed" — this is a hard budget limit, not a soft preference.
MAX_RENT_HUF = 300_000

# alberlet.hu district code for its search URL (Budapest IX. kerület).
ALBERLET_DISTRICT_CODE = "ix"

# flatco.hu is Metrodom's own management site and lists several
# buildings (Metrodom River, Green, Park, Panoráma...) — this must be
# the exact building name so flatco.py doesn't also pick up other
# Metrodom buildings' units (bare "metrodom" in ADDRESS_KEYWORDS is too
# loose for that comparison).
FLATCO_BUILDING_NAME = "metrodom green"

# Keywords (case-insensitive, Hungarian) used to detect furnishing status.
FURNISHED_KEYWORDS = ["bútorozott", "butorozott", "berendezett", "felszerelt"]
PARTIALLY_FURNISHED_KEYWORDS = ["részben bútorozott", "reszben butorozott"]
UNFURNISHED_KEYWORDS = ["bútorozatlan", "butorozatlan"]

# Keywords used to detect a terrace/balcony.
OUTDOOR_SPACE_KEYWORDS = ["erkély", "erkely", "terasz", "loggia"]

# Move-in availability: immediate, or from November 2026 onward.
IMMEDIATE_MOVE_IN_KEYWORDS = ["azonnal", "azonnal költözhető", "azonnal koltozheto"]
EARLIEST_MOVE_IN_YEAR = 2026
EARLIEST_MOVE_IN_MONTH = 11  # November

HUNGARIAN_MONTHS = {
    "január": 1, "januar": 1,
    "február": 2, "februar": 2,
    "március": 3, "marcius": 3,
    "április": 4, "aprilis": 4,
    "május": 5, "majus": 5,
    "június": 6, "junius": 6,
    "július": 7, "julius": 7,
    "augusztus": 8,
    "szeptember": 9,
    "október": 10, "oktober": 10,
    "november": 11,
    "december": 12,
}

# Only surface listings first seen within this many minutes of the current
# run (kept a bit above 60 to tolerate slow/late runs). Combined with the
# on-disk "seen" state file for deduplication.
FRESHNESS_WINDOW_MINUTES = 90

EMAIL_TO = "viktorszspam@gmail.com"
EMAIL_SUBJECT_PREFIX = "[Metrodom Green tracker]"

# Human-readable name shown in the Hungarian email header ("N új találat
# érkezett a(z) „{SEARCH_DISPLAY_NAME}” kereséshez"). Update this if the
# set of tracked buildings in ADDRESS_KEYWORDS changes — it's a separate
# value rather than derived automatically since "Metrodom Green / Cordia
# Woodland" isn't something worth reconstructing from keyword internals.
SEARCH_DISPLAY_NAME = "Metrodom Green / Cordia Woodland"

# Query text for the Facebook Marketplace no-op check (see
# scripts/scrapers/facebook.py for why this can only ever be a best-effort,
# unauthenticated check, not a real integration). Derived from the primary
# address keyword rather than hardcoded, so it stays in sync with whatever
# building this tracker is actually pointed at.
FACEBOOK_SEARCH_QUERY = ADDRESS_KEYWORDS[0]
