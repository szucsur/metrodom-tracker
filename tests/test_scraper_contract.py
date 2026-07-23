"""Every source in scripts/scrapers/ must satisfy the same contract:
a module-level fetch(session=None) -> List[Listing] that never raises,
even when the network is unavailable (check_listings.py relies on this
so one source's failure can't kill the whole run — see gather_all_listings
in scripts/check_listings.py, which still wraps each call in try/except
as defense in depth).
"""

import importlib
import inspect

import pytest

from models import Listing

SCRAPER_MODULE_NAMES = [
    "ingatlan",
    "alberlet",
    "facebook",
    "flatco",
    "rentingo",
    "albifigyelo",
    "rentola",
    "oc",
    "megveszlak",
    "tappancsosotthon",
    "maxapro",
    "koltozzbe",
]


@pytest.fixture(params=SCRAPER_MODULE_NAMES)
def scraper_module(request):
    return importlib.import_module(f"scrapers.{request.param}")


def test_scraper_exposes_fetch(scraper_module):
    assert callable(getattr(scraper_module, "fetch", None))


def test_scraper_fetch_never_raises_and_returns_a_list(scraper_module):
    # No network access in this environment — every scraper must catch its
    # own request errors internally and degrade to an empty list rather
    # than propagating an exception.
    result = scraper_module.fetch()
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, Listing)


def test_every_scraper_is_wired_into_the_single_pipeline():
    # check_listings.py is the only orchestrator — guards against a
    # scraper existing on disk but never being wired in (or the reverse),
    # which is exactly the class of bug "don't build a parallel workflow"
    # is meant to prevent.
    import check_listings

    source = inspect.getsource(check_listings)
    for name in SCRAPER_MODULE_NAMES:
        assert name in source, f"scraper module '{name}' is not referenced in check_listings.py"
