# Metrodom Green Rental Tracker

Watches Hungarian rental listing sites for new apartments matching a
location and a set of hard requirements, and emails you when a new match
appears. Built for tracking the Metrodom Green complex at 12-14 Vágóhíd
utca, Budapest 1097, but the filters in `scripts/config.py` are just data
— point them at any building, street, or district instead.

## What this does

1. **Fetches** current listings from `ingatlan.com`, `alberlet.hu`,
   `flatco.hu` (Metrodom's own property management site), `rentingo.com`,
   `albifigyelo.hu` (a nationwide listing aggregator), and `rentola.hu`.
2. **Filters** for:
   - Address/building keyword match (default: Vágóhíd utca / Metrodom Green)
     — one source (albifigyelo.hu) only matches at district level; see below
   - Minimum size and room count (default: 40 sqm, 2 rooms)
   - Furnished status, terrace/balcony, and move-in date, read from the
     listing text where stated (see "Soft filters" below)
3. **Deduplicates** against `data/seen_listings.json` so the same listing
   is never emailed twice.
4. **Emails** any new matches to the configured address.
5. Runs **hourly** via a GitHub Actions scheduled workflow
   (`.github/workflows/tracker.yml`) on GitHub's hosted runners, so it
   doesn't depend on any particular machine or session staying alive.

## ingatlan.com is blocked by Cloudflare — use its native alerts instead

Confirmed directly (not guessed): ingatlan.com sits behind a Cloudflare
bot-challenge page that returns HTTP 403 to automated requests, including
from GitHub Actions runners. `scripts/scrapers/ingatlan.py` still tries
each run in case that changes, but expect it to consistently return zero
listings — getting past it would require the same kind of anti-bot
evasion this project deliberately avoids for Facebook (see below).
**Use ingatlan.com's own saved-search email alerts** for that source.

## rentingo.com is also blocked by Cloudflare

Confirmed the same way: rentingo.com returns HTTP 403 with a genuine
Cloudflare "Attention Required!" challenge page, tested with both a
minimal header set and a fuller browser-like one — same block either
time. `scripts/scrapers/rentingo.py` still tries each run in case that
changes, but expect zero listings from this source too, for the same
anti-bot-evasion reasons as ingatlan.com and Facebook.
**Use rentingo.com's own saved-search email alerts** for that source.

## flatco.hu: the landlord's own live availability list

flatco.hu is Metrodom's own property management site (not a generic
listing portal). Its site-wide nav exposes every currently-available
rental unit directly as a link, e.g. "Metrodom Green - A.B.304" →
`/rental/metrodom-green-a-b-304/`. `scripts/scrapers/flatco.py` fetches
the homepage, picks out nav links whose building name exactly matches
`config.FLATCO_BUILDING_NAME` ("metrodom green" — kept separate from the
looser `ADDRESS_KEYWORDS` since flatco.hu also manages other Metrodom
buildings like Metrodom River/Park/Panoráma, and bare "metrodom" would
match those too), then follows each into its detail page for
price/size/rooms/furnished/terrace. This is effectively the landlord's
own "available now" list, so no district/price filtering is needed —
every link found is a genuinely open unit.

## albifigyelo.hu: district-level watch, not street-level

albifigyelo.hu is a nationwide rental-listing aggregator — it doesn't
originate listings itself, it re-publishes ones from other sites
(each listing is credited with a "Forrás:" / source, e.g. ingatlan.com,
jofogas.hu, ingatlanbazar.hu, zenga.hu), so it's a useful indirect way to
see some ingatlan.com-sourced listings even though ingatlan.com itself
is Cloudflare-blocked.

**Confirmed limitation**: neither the visible page nor the hidden
schema.org/JSON-LD data on albifigyelo.hu ever exposes a street name —
only district/neighborhood (e.g. "Budapest, Kelenföld" or "Budapest IX.
kerület") plus raw GPS coordinates. Reverse-geocoding those coordinates
to a street would mean depending on a third-party geocoding API for a
still-fuzzy result, which isn't worth the added complexity here.

So `scrapers/albifigyelo.py` is wired up as a **district-level watch**:
`Listing.location_precision = "district"` tells `filters.py` to accept a
plain "IX. kerület" match instead of requiring "Vágóhíd" text. This means
you'll get emails for **any** qualifying IX. kerület apartment from this
source, not just Vágóhíd utca specifically — each one is flagged in the
email body ("district-level match only... click through to confirm")
so you know to check the source link yourself before getting excited.

## rentola.hu: full street-level data via JSON-LD

rentola.hu (Hungarian edition of an international rental platform) embeds
every listing on its Budapest apartments page as clean schema.org
JSON-LD (`SearchResultsPage` → `ItemList` → `RealEstateListing`),
including a real `streetAddress` field, `floorSize`, `numberOfBedrooms`,
price/currency, and a `validFrom` timestamp. `scrapers/rentola.py` parses
that JSON directly rather than scraping HTML card markup — the most
robust of all the sources here, and the only one besides alberlet.hu
that gets exact street-level matching without any caveats.

One thing worth knowing: the page's default sort is "Ajánlott"
(Recommended), not strictly newest-first, and only the first batch of
listings (~10-20) is present in the initial page load — no pagination is
followed. Since a Vágóhíd utca match is rare, there's a small chance a
brand new listing could be sorted past the first page before an hourly
check catches it; no site-side sort/newest-first parameter was found
during inspection.

## What this deliberately does NOT do: Facebook/Marketplace scraping

Facebook's Terms of Service prohibit automated data collection from its
products, and Marketplace/Group content only renders for a logged-in
session. `scripts/scrapers/facebook.py` makes one unauthenticated,
no-login request and — as expected — will almost always come back empty,
because Facebook serves anonymous requests a login wall. It does not log
in, hold a session, or try to evade Facebook's bot detection.

**For Facebook coverage, use Facebook's own tools instead**: open
Marketplace, search "Vágóhíd utca" or "Metrodom Green", save the search,
and turn on notifications. Do the same for local Budapest rental
Facebook groups you're a member of. That's the reliable way to get
Facebook-sourced alerts, and it costs nothing to set up.

## Soft filters (furnished / terrace / move-in date)

Search-result pages rarely spell out every detail. When a listing's text
doesn't mention furnishing, a terrace, or a move-in date, the listing is
**kept** (not silently dropped) and flagged in the email as "verify
manually" for that field, rather than risking a false negative from an
imperfect text match. A listing IS dropped if the text explicitly says
"no terrace/balcony" equivalent, or states a move-in date earlier than
your configured earliest date.

## Setup

1. **Add repository secrets** (Settings → Secrets and variables → Actions):
   - `GMAIL_ADDRESS` — the Gmail address to send from
   - `GMAIL_APP_PASSWORD` — a Gmail [App Password](https://myaccount.google.com/apppasswords)
     (requires 2FA on that account; this is NOT your normal Gmail password)
2. The `schedule` trigger only fires on the repository's default branch,
   so once this is pushed to `main` the hourly run is active immediately
   — no PR/merge step needed for a brand-new repo.
3. Adjust `scripts/config.py` if your filters change (building, sqm,
   rooms, move-in date, recipient address).

## Manual usage

```bash
pip install -r requirements.txt
python scripts/check_listings.py --dry-run   # preview matches, no email sent
python scripts/check_listings.py             # real run: emails new matches, updates dedup state
```

`GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` must be set as environment
variables for a real (non-dry-run) run to actually send email; without
them the script prints what it would have sent instead of failing.

## Adapting to a different building or area

Edit `scripts/config.py`:

- `ADDRESS_KEYWORDS` / `LOCATION_HINTS` — what text identifies a match
- `MIN_SIZE_SQM`, `MIN_ROOMS` — hard size/room filters
- `ALBERLET_DISTRICT_CODE` — district code for alberlet.hu's search URL
- `FLATCO_BUILDING_NAME` — exact building name flatco.py watches for
  (only relevant if you're tracking a Metrodom-managed building)
- `FURNISHED_KEYWORDS`, `OUTDOOR_SPACE_KEYWORDS` — soft-filter keywords
- `EARLIEST_MOVE_IN_YEAR` / `EARLIEST_MOVE_IN_MONTH` — move-in cutoff
- `EMAIL_TO` — recipient address

## Notes on reliability

- `ingatlan.com` and `rentingo.com` are both Cloudflare-blocked (see
  above) — 0 listings from either source is expected, not a bug.
- `alberlet.hu` is verified working: a plain HTTP GET to
  `https://www.alberlet.hu/kiado-alberlet?ingatlan-tipus=lakas&kerulet=ix&meret=40-x-m2&szoba=2-x&keres=normal&limit=24`
  returns full server-rendered listings, no browser needed. Each listing's
  detail-page URL is a self-describing slug (e.g.
  `/kiado-alberlet/budapest-IX-kerulet-vagohid-utca-65m2-3-szoba_779416`)
  that encodes district, street, size, and room count — `alberlet.py`
  parses that directly rather than relying on CSS classes, which should
  hold up better across redesigns. If a run starts returning 0 listings
  here, check the Actions log for the actual HTTP status/error first.
