"""Shared data model for listings across all sources."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    source: str            # "ingatlan.com" | "alberlet.hu" | "facebook"
    listing_id: str         # stable id/url used for dedup
    url: str
    title: str
    price_text: str = ""
    size_sqm: Optional[float] = None
    rooms: Optional[float] = None
    address_text: str = ""
    description_text: str = ""
    posted_at: Optional[str] = None  # ISO string if known

    # "exact" (default): address_text is expected to name the actual
    # street, so ADDRESS_KEYWORDS must match for location_matches().
    # "district": this source only ever exposes district/neighborhood
    # level location (no street name available anywhere, even in
    # structured data) — location_matches() accepts a LOCATION_HINTS-only
    # match instead, and filters.py flags these listings as needing
    # manual street confirmation.
    location_precision: str = "exact"

    # Filled in by filters.py — None means "could not be determined from
    # the listing text", not "fails the filter".
    furnished_status: Optional[str] = None   # "full" | "partial" | "none" | None
    has_outdoor_space: Optional[bool] = None
    move_in_ok: Optional[bool] = None

    # Display-only enrichment, filled in by filters.enrich_for_display()
    # right before a listing is emailed — never used for filtering,
    # matching, or dedup, so populating these late doesn't affect any of
    # that. None means "not detected", not "confirmed absent".
    district: Optional[str] = None          # e.g. "IX. kerület"
    display_name: Optional[str] = None      # title with any district prefix stripped
    street_address: Optional[str] = None    # a real street address, if found
    orientation: Optional[str] = None       # "north" | "south" | ... | None

    notes: list = field(default_factory=list)

    def dedup_key(self) -> str:
        return f"{self.source}:{self.listing_id}"
