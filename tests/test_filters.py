import filters
from models import Listing


def make_listing(**overrides):
    defaults = dict(
        source="test",
        listing_id="1",
        url="https://example.com/1",
        title="",
        address_text="",
        description_text="",
        size_sqm=45,
        rooms=2,
        price_text="250 000 Ft/hó",
    )
    defaults.update(overrides)
    return Listing(**defaults)


def test_exact_street_match_passes():
    listing = make_listing(
        title="Metrodom Green - A.B.304",
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca Budapest, IX. kerület",
    )
    assert filters.passes_hard_filters(listing)


def test_other_metrodom_building_is_rejected():
    # Regression: bare "metrodom" used to short-circuit location_matches()
    # and match any Metrodom-branded building regardless of district.
    listing = make_listing(
        title="IV. Metrodom Panoráma",
        address_text="IV. Metrodom Panoráma",
        description_text="IV. Metrodom Panoráma, Budapest IV. kerület",
    )
    assert not filters.passes_hard_filters(listing)


def test_other_cordia_project_is_rejected():
    listing = make_listing(
        title="Cordia Corvin Offices - kiadó lakás",
        address_text="Cordia Corvin Offices",
        description_text="Cordia Corvin Offices, Budapest",
    )
    assert not filters.passes_hard_filters(listing)


def test_cordia_woodland_matches():
    listing = make_listing(
        title="Cordia Woodland - kiadó lakás",
        address_text="Cordia Woodland",
        description_text="Cordia Woodland, Budapest",
    )
    assert filters.passes_hard_filters(listing)


def test_district_precision_matches_on_district_alone():
    listing = make_listing(
        address_text="Budapest IX. kerület, Ferencváros",
        description_text="Budapest IX. kerület, Ferencváros",
        location_precision="district",
    )
    assert filters.passes_hard_filters(listing)
    filters.passes_soft_filters(listing)
    assert any("district-level" in note for note in listing.notes)


def test_too_small_fails_hard_filter():
    listing = make_listing(
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca",
        size_sqm=30,
    )
    assert not filters.passes_hard_filters(listing)


def test_too_few_rooms_fails_hard_filter():
    listing = make_listing(
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca",
        rooms=1,
    )
    assert not filters.passes_hard_filters(listing)


def test_price_at_cap_passes():
    listing = make_listing(
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca",
        price_text="300 000 Ft/hó",
    )
    assert filters.passes_hard_filters(listing)


def test_price_over_cap_fails():
    listing = make_listing(
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca",
        price_text="350 000 Ft/hó",
    )
    assert not filters.passes_hard_filters(listing)


def test_unparseable_price_fails_hard_filter():
    # A hard budget cap, not a soft preference — unlike size/rooms it
    # never falls back to "keep and flag unconfirmed".
    listing = make_listing(
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca",
        price_text="Ár érdeklődésre",
    )
    assert not filters.passes_hard_filters(listing)


def test_parse_price_huf_formats():
    cases = {
        "220 000 Ft/hó": 220000,
        "250 000 HUF/hónap": 250000,
        "220000 HUF/hónap": 220000,
        "180e Ft": 180000,
        "220000": 220000,
        "500 €": None,
        "": None,
    }
    for text, expected in cases.items():
        assert filters.parse_price_huf(text) == expected


def test_soft_filter_keeps_unconfirmed_details():
    listing = make_listing(
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca Budapest, IX. kerület",
    )
    filters.annotate(listing)
    assert filters.passes_soft_filters(listing)
    assert any("furnished" in note for note in listing.notes)
    assert any("terrace" in note for note in listing.notes)
    assert any("move-in" in note for note in listing.notes)


def test_soft_filter_drops_explicit_contradiction():
    # detect_outdoor_space() is plain substring matching, not
    # negation-aware (a pre-existing, documented-nowhere limitation across
    # this project — "nincs erkély" still contains "erkély" and would be
    # mis-detected as True). That's out of scope here; this test pins down
    # passes_soft_filters()'s actual contract directly: an explicit False
    # drops the listing, regardless of how it got set.
    listing = make_listing(
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca",
    )
    listing.has_outdoor_space = False
    assert not filters.passes_soft_filters(listing)


def test_apply_all_end_to_end():
    good = make_listing(
        listing_id="good",
        title="Vágóhíd utca Metrodom Green",
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Vágóhíd utca Budapest, IX. kerület",
    )
    bad = make_listing(
        listing_id="bad",
        title="XI. Metrodom",
        address_text="XI. Metrodom",
        description_text="XI. Metrodom, Budapest XI. kerület",
    )
    matches = filters.apply_all([good, bad])
    assert [m.listing_id for m in matches] == ["good"]
