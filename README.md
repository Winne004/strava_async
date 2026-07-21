# strava-async

An async Python client for the [Strava API v3](https://developers.strava.com/docs/reference/).

Fully typed, `asyncio`-native, and declarative: every request body and query string is a
Pydantic model, every response is validated into one. All 34 operations in the official
Swagger spec are covered across nine services.

```python
from datetime import UTC, datetime

from strava_async import initialise_strava_client
from strava_async.schemas.params import GetActivitiesParams

async with initialise_strava_client() as client:
    athlete = await client.athletes.get_logged_in_athlete()
    activities = await client.activities.get_logged_in_athlete_activities(
        GetActivitiesParams(per_page=50, after=datetime(2026, 1, 1, tzinfo=UTC))
    )

    print(f"{athlete.firstname}: {len(activities)} activities")
```

> **Status: pre-release.** The request pipeline, auth, and parameter handling are well
> covered by tests. The *response* models for several endpoints were written from Strava's
> documentation rather than from recorded live responses — see
> [Known limitations](#known-limitations) before relying on them in production.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
uv add strava-async
```

For local development:

```bash
git clone https://github.com/Winne004/strava_async.git
cd strava_async
uv sync
```

## Authentication

Strava uses OAuth 2.0 with the authorization-code grant. This library does **not** run the
interactive browser leg — it takes a refresh token you already hold and exchanges it for
short-lived access tokens.

### One-time setup

1. Create an application at https://www.strava.com/settings/api and note the **Client ID**
   and **Client Secret**.
2. Complete the authorization flow once to obtain a refresh token for your athlete, with
   the scopes you need (see below).
3. Put the three values in the environment:

```bash
export STRAVA_CLIENT_ID="12345"
export STRAVA_CLIENT_SECRET="..."
export STRAVA_REFRESH_TOKEN="..."
```

These are read by pydantic-settings, so a `.env` file works too. **Do not commit it.**

### Refresh-token rotation

Strava may issue a **new refresh token** on every exchange. If you discard it, your stored
credential eventually stops working. Pass a callback to capture it:

```python
def persist(new_refresh_token: str) -> None:
    ...  # write it to your secret store

async with initialise_strava_client(on_token_refresh=persist) as client:
    ...
```

### Scopes

Each service method's docstring names the scope it needs. A missing scope surfaces as a
`403` at runtime, not at import time.

| Scope | Grants |
| --- | --- |
| `read` | Public segments, routes, profile, posts, events, club feeds |
| `read_all` | Private routes, segments, and events |
| `profile:read_all` | Full profile regardless of visibility settings |
| `profile:write` | Update weight/FTP; star and unstar segments |
| `activity:read` | Activities visible to Everyone/Followers, no privacy-zone data |
| `activity:read_all` | Plus privacy-zone data and "Only You" activities |
| `activity:write` | Create manual activities and uploads; edit visible activities |

## Usage

### The client is a context manager

The client owns an `aiohttp` session, so it must be used with `async with`. Services are
created lazily on first access and cached for the life of the context; touching one outside
the context raises `RuntimeError`.

```python
async with initialise_strava_client() as client:
    segment = await client.segments.get_segment_by_id(229781)
```

To share a session you already manage, pass it in — the client will use it and will not
close it:

```python
async with aiohttp.ClientSession() as session:
    async with initialise_strava_client(session=session) as client:
        ...
```

### Services

| Service | Covers |
| --- | --- |
| `client.activities` | Activities, comments, kudos, laps, zones |
| `client.athletes` | Profile, zones, aggregate stats |
| `client.clubs` | Clubs, members, admins, activity feed |
| `client.gear` | Bikes and shoes |
| `client.routes` | Routes and their GPX/TCX exports |
| `client.segments` | Segments, the explorer, starred segments |
| `client.segment_efforts` | Your attempts at segments |
| `client.streams` | Per-sample time series for four resource types |
| `client.uploads` | Activity file uploads |

### Structured input, structured output

Path parameters are plain scalars. Everything else — bodies and query strings — is a model,
and the model owns the wire format. You never build a query string or encode a date.

```python
from strava_async.schemas.params import ExploreSegmentsParams, StreamParams
from strava_async.schemas.segment_model import StarSegmentRequestBody

# `bounds` is serialised to CSV; the climb-category range is validated before the request
found = await client.segments.explore_segments(
    ExploreSegmentsParams(bounds=[37.8, -122.5, 37.9, -122.4], min_cat=1, max_cat=4)
)

# `keys` becomes CSV, and key_by_type is pinned to true
streams = await client.streams.get_activity_streams(
    12345, StreamParams(keys=["time", "heartrate", "watts"])
)
print(streams.heartrate.data if streams.heartrate else "no heart-rate data")

await client.segments.star_segment(229781, StarSegmentRequestBody(starred=True))
```

Invalid input fails at construction, before any network call:

```python
ExploreSegmentsParams(bounds=[1.0, 2.0, 3.0])              # needs exactly four
ExploreSegmentsParams(bounds=[...], min_cat=4, max_cat=2)  # inverted range
GetActivitiesParams(after=datetime(2026, 1, 1))            # must be timezone-aware
```

That last one is deliberate: `before`/`after` are sent as epoch seconds, and converting a
naive datetime would silently depend on the machine's local timezone.

### Uploads are asynchronous

`create_upload` returns as soon as Strava accepts the file. Poll until it settles — the
client deliberately does not hide the wait:

```python
from strava_async.schemas.upload_model import CreateUploadRequestBody

with open("ride.gpx", "rb") as handle:
    upload = await client.uploads.create_upload(
        CreateUploadRequestBody(data_type="gpx", name="Morning Ride"), handle
    )

while not upload.is_complete:
    await asyncio.sleep(2)
    upload = await client.uploads.get_upload_by_id(upload.id)

print(upload.activity_id or upload.error)
```

## Errors

Everything derives from `StravaError`, so you can catch one type or discriminate by branch.

```python
from strava_async import StravaNotFoundError, StravaPermissionError, StravaRateLimitError

try:
    activity = await client.activities.get_activity_by_id(1)
except StravaPermissionError:
    ...  # token lacks the scope, or the resource is private — not retryable
except StravaNotFoundError as error:
    print(error.status_code, error.endpoint, error.details)
except StravaRateLimitError as error:
    print(f"retry in {error.retry_after}s", error.details)
```

`StravaClientError` (4xx) and `StravaServerError` (5xx) are the two branches, plus
`StravaConnectionError` for transport failures. Strava's error body is attached to
`error.details`; parse it with `Fault.model_validate(error.details)` if you want it typed.

## Rate limits and retries

Strava's quota is **per application**, not per endpoint, so one shared limiter paces every
service. Transient failures — connection errors, `401`, and `429` — are retried with
backoff; a `403` is not, since refreshing a token cannot add a scope that was never granted.

Because Strava does not reliably send `Retry-After`, a `429` falls back to the time
remaining in the current 15-minute window, capped by `max_retry_wait_seconds` so it never
becomes a quarter-hour hang.

The defaults are Strava's published figures, but limits are set per application and have
changed over time. **Check yours** at
[developers.strava.com/docs/rate-limits](https://developers.strava.com/docs/rate-limits)
and override as needed:

```bash
export STRAVA_REQUESTS_PER_QUARTER_HOUR=200
export STRAVA_DAILY_REQUEST_LIMIT=2000
```

### All settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `STRAVA_CLIENT_ID` | — | Required |
| `STRAVA_CLIENT_SECRET` | — | Required |
| `STRAVA_REFRESH_TOKEN` | — | Required |
| `STRAVA_BASE_URL` | `https://www.strava.com/api/v3` | API root |
| `STRAVA_TOKEN_URL` | `.../oauth/token` | Token endpoint |
| `STRAVA_REQUESTS_PER_QUARTER_HOUR` | `100` | Short-window budget |
| `STRAVA_DAILY_REQUEST_LIMIT` | `1000` | Daily budget (see limitations) |
| `STRAVA_MAX_RETRY_ATTEMPTS` | `4` | Total attempts, including the first |
| `STRAVA_MAX_RETRY_WAIT_SECONDS` | `60` | Ceiling on any single backoff |
| `STRAVA_TOKEN_EXPIRY_MARGIN_SECONDS` | `300` | Refresh this early |
| `STRAVA_CONNECTOR_LIMIT` | `10` | Max simultaneous connections |
| `STRAVA_REQUEST_TIMEOUT_SECONDS` | `30` | Total per-request timeout |

## Known limitations

Worth reading before you depend on this:

- **Some response models are unverified.** The spec embeds example payloads for many
  endpoints but not all. Models for `Route`, `Upload`, `ActivityStats`, `Zones`,
  `ActivityZone` and a few others were written from Strava's documentation rather than
  recorded responses. Because response fields are all optional, a wrong field name reads as
  `None` rather than raising — so a mistake here is quiet. Verify against live data before
  trusting these.
- **The daily rate limit is not enforced.** `STRAVA_DAILY_REQUEST_LIMIT` is read but
  currently unused; only the 15-minute window is paced.
- **No pagination helper.** List endpoints take `page`/`per_page` and return one page. There
  is no auto-paginating iterator — deliberate for now, but you will write that loop yourself.
- **Two spec defects are worked around.** `PUT /athlete` declares `weight` as a path
  parameter, which cannot be right; it is sent as a form field. The `/athlete/zones` example
  block shows an activity-zone payload rather than the schema it references; the model
  follows the referenced schema.

## Development

```bash
uv sync
uv run pytest
uv run ruff check --fix
uv run ruff format
uv run ty check
```

The suite is offline and clock-free — no network, no real sleeps, no dependence on the
current time.

`tests/test_architecture.py` parses the source to enforce the design: import boundaries
between layers, and the declarative service style (one delegating call per method, no
`dict`/`Any` in a signature). It also asserts the endpoint count against the spec, so a new
endpoint that skips a model or hides logic in a service fails the suite.

Contributions should follow the patterns in [CLAUDE.md](CLAUDE.md), which documents the
architecture and the change recipes for adding an endpoint, a service, or an error type.

## License

Not yet licensed. Add one before depending on this.
