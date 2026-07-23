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


def test_metrodom_city_home_matches_as_the_nadasdy_utca_building():
    # "Metrodom City Home" turned out to be the marketing name for the
    # building at the Nádasdy utca address (confirmed with the user), not
    # an unrelated Metrodom building — unlike "IV. Metrodom Panoráma" and
    # "IX. Metrodom City Home" was previously (incorrectly) treated as one
    # of those false positives; it's now an explicit ADDRESS_KEYWORDS entry.
    listing = make_listing(
        title="IX. Metrodom City Home",
        address_text="IX. Metrodom City Home",
        description_text="IX. Metrodom City Home, Budapest IX. kerület",
    )
    assert filters.passes_hard_filters(listing)


def test_bare_cordia_and_generic_lakopark_brands_are_rejected():
    cases = [
        "Cordia Lakópark",
        "Metrodom Lakópark",
        "Green Lakópark",
    ]
    for text in cases:
        listing = make_listing(
            title=text,
            address_text=f"{text}, Budapest IX. kerület",
            description_text=f"{text}, Budapest IX. kerület",
        )
        assert not filters.passes_hard_filters(listing), text


def test_metrodom_green_lakopark_full_name_matches():
    listing = make_listing(
        title="Kiadó lakás a Metrodom Green Lakóparkban",
        address_text="Vágóhíd utca Budapest, IX. kerület",
        description_text="Metrodom Green Lakópark, IX. kerület",
    )
    assert filters.passes_hard_filters(listing)


def test_cordia_woodland_lakopark_full_name_matches():
    listing = make_listing(
        title="Kiadó lakás a Cordia Woodland Lakóparkban",
        address_text="Budapest, IX. kerület",
        description_text="Cordia Woodland Lakópark, IX. kerület",
    )
    assert filters.passes_hard_filters(listing)


def test_nadasdy_utca_matches_as_a_second_address():
    listing = make_listing(
        title="Kiadó lakás Nádasdy utcában",
        address_text="Nádasdy utca Budapest, IX. kerület",
        description_text="Nádasdy utca 4, Metrodom Green lakópark",
    )
    assert filters.passes_hard_filters(listing)


def test_nadasdy_utca_variants_all_match_via_substring():
    # Confirms the substring-matching design already covers every spelling
    # variant (abbreviation, house number, postal code, district prefix)
    # without needing them listed separately in config.
    variants = [
        "Nádasdy u.",
        "Nádasdy utca 4",
        "Nádasdy u. 4",
        "1097 Nádasdy utca",
        "1097 Budapest, Nádasdy utca",
        "Budapest IX. kerület, Nádasdy utca",
        "IX. kerület Nádasdy utca",
    ]
    for text in variants:
        listing = make_listing(title=text, address_text=text, description_text=text)
        assert filters.passes_hard_filters(listing), text


def test_vagohid_utca_variants_all_match_via_substring():
    variants = [
        "Vágóhíd u.",
        "Vágóhíd utca 12-14",
        "Vágóhíd u. 12-14",
        "Vágóhíd utca 12–14",
        "Vágóhíd utca 9",
        "1097 Vágóhíd utca 9",
        "1097 Budapest, Vágóhíd utca 9",
        "Budapest IX. kerület, Vágóhíd utca",
        "IX. kerület Vágóhíd utca",
    ]
    for text in variants:
        listing = make_listing(title=text, address_text=text, description_text=text)
        assert filters.passes_hard_filters(listing), text


def test_neighborhood_hint_alone_is_not_sufficient_for_exact_precision():
    # "Keep it building-specific": a neighborhood/landmark mention, even
    # combined with a generic "new build" phrase, must never be enough on
    # its own for a source that's supposed to give an exact street match.
    listing = make_listing(
        title="Új, modern lakás kiadó",
        address_text="Ferencváros, közel a Müpához",
        description_text="Újépítésű, modern lakás Ferencvárosban, a Duna-parton, közel a Könyves Kálmán körúthoz.",
    )
    assert not filters.passes_hard_filters(listing)


def test_neighborhood_hint_alone_still_works_for_district_precision_source():
    # Unchanged, pre-existing behavior for sources that structurally can
    # never expose a street name (albifigyelo.hu/megveszlak.hu) — this is
    # the same "district watch" tradeoff chosen earlier, just with more
    # trigger phrases now available for it.
    listing = make_listing(
        title="Kiadó lakás Ferencvárosban",
        address_text="Ferencváros, Budapest",
        description_text="Kiadó lakás Ferencvárosban, a Müpa közelében.",
        location_precision="district",
    )
    assert filters.passes_hard_filters(listing)


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
