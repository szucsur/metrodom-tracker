"""Best-effort, unauthenticated check of Facebook Marketplace/Groups.

## Why this can't be a real integration

Facebook Marketplace has no public API for peer-to-peer rental listings —
the Graph API surface that once exposed Marketplace search was withdrawn
from general developer access years ago, and nothing an individual
developer can apply for exposes it today.

Marketplace and Group content only renders to a logged-in session. That
means the *only* way to retrieve real listing data here would be to
automate a session that is actually authenticated — and that's true
regardless of whether CAPTCHAs are solved or bot-detection is evaded.
Facebook's Terms of Service prohibit automated data collection from its
products, full stop; "don't bypass access controls" and "don't violate
ToS" together rule out the only path that would produce real results, not
just the crude versions of it.

So this module deliberately does NOT log in, hold a session/cookie jar,
store or read any Facebook session/cookie data, spoof a browser
fingerprint, or otherwise try to get around Facebook's bot detection. It
issues a single plain, unauthenticated GET to a public search URL and
nothing more. In practice this reliably returns a login-wall redirect,
which is expected and by design, not a bug — confirmed directly against
the live site, not assumed.

No Facebook session, cookie, or credential data is ever read, written, or
committed by this module or by the tracker generally (see the Facebook
patterns in .gitignore, which exist as a guardrail even though nothing
here creates such a file).

**For real Facebook coverage, use Facebook's own tools**: open
Marketplace, search for the building/street, save the search, and turn on
notifications. Do the same for local Budapest rental Facebook groups
you're a member of — that's the reliable way to get Facebook-sourced
alerts, and it costs nothing to set up.
"""

from typing import List

import requests

import config
from models import Listing

SEARCH_URL_TEMPLATE = "https://www.facebook.com/marketplace/108314429191488/search/?query={query}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}


def _search_url() -> str:
    from urllib.parse import quote

    return SEARCH_URL_TEMPLATE.format(query=quote(config.FACEBOOK_SEARCH_QUERY))


def fetch(session: requests.Session = None) -> List[Listing]:
    session = session or requests.Session()
    try:
        resp = session.get(_search_url(), headers=HEADERS, timeout=15, allow_redirects=True)
    except requests.RequestException as exc:
        print(f"[facebook] request failed (expected without login): {exc}")
        return []

    if "login" in resp.url or resp.status_code in (302, 400, 403, 429):
        print(
            "[facebook] no data available without an authenticated session "
            "(this is expected — see module docstring). Use Marketplace's "
            "native saved-search alerts instead."
        )
        return []

    # We deliberately don't attempt to parse Facebook's markup even if a
    # response came back, since any real result here is unauthenticated
    # public content only (e.g. a fully public group post rendered
    # server-side), which is rare enough not to be worth building a parser
    # around.
    return []
