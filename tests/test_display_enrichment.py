"""filters.compute_display_fields() / enrich_for_display() derive extra
fields for the email template (district, a cleaned display name, a real
street address, orientation). None of this participates in filtering,
matching, or dedup — these tests only check the derivation itself.
"""

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
    )
    defaults.update(overrides)
    return Listing(**defaults)


def test_leading_district_prefix_is_split_into_district_and_name():
    listing = make_listing(title="IV. Metrodom Panoráma")
    filters.enrich_for_display(listing)
    assert listing.district == "IV. kerület"
    assert listing.display_name == "Metrodom Panoráma"


def test_leading_district_prefix_with_street_name_does_not_duplicate_as_address():
    # "VII. Csányi utca" already shows the street name in the headline via
    # the leading-district split — a separate Cím line would just repeat it.
    listing = make_listing(title="VII. Csányi utca")
    filters.enrich_for_display(listing)
    assert listing.district == "VII. kerület"
    assert listing.display_name == "Csányi utca"
    assert listing.street_address is None


def test_district_mentioned_in_address_text_does_not_duplicate_as_address():
    # The headline already leads with "Vágóhíd utca" here too (alberlet.hu
    # doesn't cleanly split district from name), so no separate Cím line.
    listing = make_listing(
        title="Vágóhíd utca - 65 m2, 3 szoba",
        address_text="Vágóhíd utca Budapest, IX. kerület",
    )
    filters.enrich_for_display(listing)
    assert listing.district == "IX. kerület"
    assert listing.street_address is None


def test_no_district_detected_falls_back_to_title_only():
    listing = make_listing(title="Kellemes lakás kiadó")
    filters.enrich_for_display(listing)
    assert listing.district is None
    assert listing.display_name == "Kellemes lakás kiadó"


def test_street_address_not_duplicated_when_it_equals_the_display_name():
    # Regression guard for the dedup check itself: it must actually
    # suppress the duplicate rather than compare a value against itself
    # and trivially pass.
    listing = make_listing(title="VII. Csányi utca")
    filters.enrich_for_display(listing)
    assert listing.street_address is None
    assert listing.display_name == "Csányi utca"


def test_district_only_address_text_never_becomes_a_fake_street_address():
    listing = make_listing(
        title="Kiadó tégla lakás Budapest IX. kerület",
        address_text="Budapest IX. kerület, Ferencváros",
        location_precision="district",
    )
    filters.enrich_for_display(listing)
    assert listing.street_address is None


def test_street_address_shown_when_genuinely_not_duplicated():
    # rentola.hu-style: a clean, structured streetAddress field separate
    # from a generic title that never mentions the street — this is the
    # case where a Cím line adds real information, so it should show.
    listing = make_listing(
        title="Kiadó lakás Ferencvárosban",
        address_text="Vágóhíd utca 12-14",
    )
    filters.enrich_for_display(listing)
    assert listing.street_address == "Vágóhíd utca 12-14"


def test_project_name_with_ambiguous_word_is_not_treated_as_street():
    # "Marina part" doesn't contain a whitelisted street-type suffix
    # (utca/út/körút/tér/sétány/köz/dűlő/fasor/rakpart) — deliberately
    # conservative, since it's a development/area name, not a street.
    listing = make_listing(title="XIII. Marina part")
    filters.enrich_for_display(listing)
    assert listing.district == "XIII. kerület"
    assert listing.street_address is None


def test_orientation_detected_from_description():
    listing = make_listing(description_text="Napfényes, délnyugati fekvésű lakás.")
    filters.enrich_for_display(listing)
    assert listing.orientation == "southwest"


def test_orientation_compound_direction_not_truncated_to_simple_direction():
    for text, expected in [
        ("északkeleti tájolású", "northeast"),
        ("északnyugati fekvés", "northwest"),
        ("délkeleti erkély", "southeast"),
        ("délnyugati napfény", "southwest"),
    ]:
        listing = make_listing(description_text=text)
        filters.enrich_for_display(listing)
        assert listing.orientation == expected, text


def test_orientation_not_mentioned_stays_none():
    listing = make_listing(description_text="Szép, felújított lakás.")
    filters.enrich_for_display(listing)
    assert listing.orientation is None


def test_unfurnished_keyword_detected_as_none_furnished_status():
    listing = make_listing(description_text="Bútorozatlan lakás kiadó.")
    filters.annotate(listing)
    assert listing.furnished_status == "none"


def test_unfurnished_does_not_collide_with_furnished_keyword_matching():
    # Regression guard: "bútorozott" must not be mistakenly detected
    # inside "bútorozatlan" or vice versa.
    listing = make_listing(description_text="Teljesen bútorozott lakás.")
    filters.annotate(listing)
    assert listing.furnished_status == "full"
