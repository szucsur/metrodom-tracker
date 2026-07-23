"""Facebook is a documented no-op by design (see scripts/scrapers/facebook.py
docstring for why a real integration isn't possible without violating
Facebook's Terms of Service). These tests pin down that contract with
mocked responses so it can't silently regress into something that tries
to hold a session or parse authenticated content.
"""

import inspect

import scrapers.facebook as facebook


class _FakeResponse:
    def __init__(self, url, status_code=200):
        self.url = url
        self.status_code = status_code


class _FakeSession:
    def __init__(self, response):
        self._response = response
        self.get_calls = []

    def get(self, url, headers=None, timeout=None, allow_redirects=None):
        self.get_calls.append(url)
        return self._response


def test_login_wall_redirect_yields_no_listings():
    session = _FakeSession(_FakeResponse("https://www.facebook.com/login/?next=..."))
    assert facebook.fetch(session) == []


def test_non_200_status_yields_no_listings():
    for status in (302, 400, 403, 429):
        session = _FakeSession(_FakeResponse("https://www.facebook.com/marketplace/", status))
        assert facebook.fetch(session) == []


def test_unexpected_200_still_returns_empty_without_parsing():
    # Even in the (rare) case a plain GET comes back 200, this module must
    # not attempt to parse the page — see the module docstring for why.
    session = _FakeSession(_FakeResponse("https://www.facebook.com/marketplace/108314429191488/search/"))
    assert facebook.fetch(session) == []


def test_search_query_is_config_driven_not_hardcoded():
    from urllib.parse import parse_qs, urlparse

    import config

    url = facebook._search_url()
    query_param = parse_qs(urlparse(url).query)["query"][0]
    assert query_param == config.FACEBOOK_SEARCH_QUERY


def test_no_session_cookie_or_browser_automation_imports():
    # Static guard against this module quietly growing a login/session
    # path (playwright, selenium, http.cookiejar, etc.) — a real
    # integration would require exactly that, and this project has
    # decided not to build it. See the module docstring for the full
    # reasoning.
    source = inspect.getsource(facebook)
    forbidden = ["playwright", "selenium", "cookiejar", "login(", "password"]
    lowered = source.lower()
    for token in forbidden:
        assert token not in lowered, f"facebook.py must not reference '{token}'"
