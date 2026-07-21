# CLAUDE.md

Repository guidance for AI coding agents and contributors working on `strava_async`.

Status: greenfield. Only `main.py` and `pyproject.toml` exist so far — the layout and
patterns below describe the target design, not code you will find on disk yet. Build
toward them; do not invent a second structure.

The API surface is pinned by `context/strava_swagger.json` (Strava API v3, Swagger 2.0).
Treat that file as the source of truth for paths, parameters, enums, and required scopes.

## Project Summary

- **Package:** `strava_async` (distribution name `strava-async`)
- **Purpose:** async Python client for the Strava API v3
- **Python:** `>=3.13`
- **Package manager:** uv only
- **Core stack:** aiohttp, pydantic, pydantic-settings, aiolimiter, tenacity
- **Base URL:** `https://www.strava.com/api/v3` (one host for every service — see
  "Service registry and limits" for why that matters)

## Mandatory Tooling Rules

Use uv exclusively for dependency management and command execution. Never use pip,
poetry, or conda directly in this repo.

| Task | Command |
| --- | --- |
| Install/sync env | `uv sync` |
| Add runtime dependency | `uv add <package>` |
| Add dev dependency | `uv add --group dev <package>` |
| Remove dependency | `uv remove <package>` |
| Re-lock dependencies | `uv lock` |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check --fix` |
| Format | `uv run ruff format` |
| Type check | `uv run ty check` |
| Pre-commit (all files) | `uv run pre-commit run --all-files` |

## Local Development

1. Sync the environment: `uv sync`
2. Set credentials for local integration use:
   ```
   export STRAVA_CLIENT_ID="..."
   export STRAVA_CLIENT_SECRET="..."
   export STRAVA_REFRESH_TOKEN="..."
   ```
   These are read by pydantic-settings in `settings.py`; names must match the settings
   field names (case-insensitively, including any `env_prefix`).
3. Run tests and quality checks before finishing changes: `uv run pytest`,
   `uv run ruff check --fix`, `uv run ruff format`, `uv run ty check`.

Get a refresh token by running the OAuth authorization-code flow once against your own
app at https://www.strava.com/settings/api. The Swagger Playground
(https://developers.strava.com/playground) is the fastest way to see a real response
shape before writing models.

## Repository Layout

```
src/strava_async/
  client.py        # StravaClient: async context manager, lazy service properties
  initialise.py    # initialise_strava_client(): builds settings, registry, auth, client
  settings.py      # pydantic-settings: OAuth credentials + base URL + rate limits
  registry.py      # service name -> (class, base_url, rate limit)
  protocols.py     # structural types (e.g. AuthClientProtocol) — no internal imports
  exceptions.py    # exception hierarchy + HTTP status -> exception mapping
  auth/            # token refresh, caching, invalidation
  services/
    base.py            # Base: the whole request pipeline lives here
    activities.py      # /activities, /athlete/activities
    athletes.py        # /athlete, /athlete/zones, /athletes/{id}/stats
    clubs.py           # /clubs/..., /athlete/clubs
    gear.py            # /gear/{id}
    routes.py          # /routes/..., /athletes/{id}/routes
    segments.py        # /segments/...
    segment_efforts.py # /segment_efforts...
    streams.py         # /{resource}/{id}/streams
    uploads.py         # /uploads
  schemas/         # Pydantic models: responses, form bodies, query params
tests/             # pytest suite, mirrors the src layout
context/           # strava_swagger.json — the pinned API contract
```

## Architecture Notes

### Layering (enforced by `tests/test_architecture.py`)

```
settings / protocols / exceptions / auth   <- foundation: no internal imports at all
schemas                                    <- may import stdlib + pydantic only
services/base.py                           <- imports protocols + exceptions only
services/<service>.py                      <- imports base + schemas + protocols
registry.py                                <- imports services + settings
client.py                                  <- imports services + registry + protocols
initialise.py                              <- imports everything; the only wiring point
```

Rules of thumb:

- Dependencies point downward only. A lower layer never imports a higher one.
- `client.py` must not import settings or the concrete auth client — it receives a
  registry and an auth class (typed via `protocols.py`) so it stays substitutable.
- Domain services never import `client`, `registry`, `settings`, or the auth module.
- `services/base.py` never imports a sibling service or any schema.

### Client lifecycle

Construct with `initialise_strava_client()` — never by hand in application code. Always
use the client as an async context manager:

```python
async with initialise_strava_client() as client:
    activities = await client.activities.get_logged_in_athlete_activities(
        GetActivitiesParams(per_page=50, after=datetime(2026, 1, 1, tzinfo=UTC))
    )
```

`__aenter__` creates the `aiohttp.ClientSession` (with a bounded `TCPConnector`) unless
an external session was injected; `__aexit__` closes it only if the client owns it, then
clears cached services and the auth client. The auth client and each service are lazily
created on first access and cached for the lifetime of the context. Accessing them
outside the context raises `RuntimeError`.

### Request pipeline

All network I/O funnels through `Base` in `services/base.py`:

1. Acquire auth headers (skipped when the caller passes explicit headers).
2. Acquire a slot from the shared `AsyncLimiter` (rate limiting).
3. Issue the request with aiohttp.
4. `_raise_for_status` maps the HTTP status to a typed exception, attaching
   `status_code`, `endpoint`, and the response body in `details`. Strava error bodies
   follow `fault.json#/Fault` — `{"message": ..., "errors": [{"resource", "field",
   "code"}]}` — so parse and surface `errors` rather than dumping raw text.
5. tenacity retries transient failures (connection errors, auth errors, 429) with
   backoff; see "Rate limits" for why Retry-After is not enough here.
6. For JSON endpoints, the body is validated into the caller-supplied Pydantic model.

`Base` exposes:

| Helper | Use for |
| --- | --- |
| `fetch_data` | JSON responses, validated against a model |
| `_post_form` | `application/x-www-form-urlencoded` bodies (Strava writes) |
| `_post_multipart` | `multipart/form-data` with a file part (`POST /uploads`) |
| `_put_form` | form-encoded PUT bodies (`PUT /athlete`, `PUT /segments/{id}/starred`) |
| `_delete` | DELETE with no response body |
| `_get_text` | text/XML responses (`export_gpx`, `export_tcx`) |
| `_get_bytes` | binary responses |

Every helper takes `endpoint`, an optional `params` model, an optional `payload` model,
and (except `_delete`/`_get_text`/`_get_bytes`) a `model` to validate the response into.
`fetch_data` is strictly for validated JSON out. For anything else use a helper above —
never bypass them with a raw `self._session.request(...)`, or you lose rate limiting,
retries, and error mapping.

**Strava-specific:** the v3 API takes **form data, not JSON**, on every write. `POST
/activities` and `PUT /segments/{id}/starred` take `formData` fields; `PUT /athlete` and
`POST /uploads` are `multipart/form-data`. Every response is JSON except the two route
exports. So `fetch_data` covers reads only — plan the write helpers accordingly.

### Service methods are declarative

A service method is a **declaration of an endpoint, not a procedure**. It names the URL,
the input model, the output model, and the verb — then hands off. The canonical shape:

```python
async def create_activity(self, activity: CreateActivityRequestBody) -> DetailedActivity:
    """Create a manual activity. Requires activity:write scope.

    Args:
        activity: The activity to create.

    Returns:
        The created activity's detailed representation.
    """
    return await self._post_form(
        endpoint=f"{self.base_url}/activities",
        model=DetailedActivity,
        payload=activity,
    )
```

Non-negotiables:

- **Every structured input is a Pydantic model.** Bodies and query-param sets are models
  in `schemas/`, not `dict`s, not `**kwargs`, not a long list of loose keyword arguments.
  Only path parameters are passed as bare scalars, since they are interpolated into the
  URL and not serialized.
- **Every output is a Pydantic model** (or `list[Model]`, `str`, `bytes`). Never
  `dict[str, Any]`, never a raw `aiohttp` response.
- **No `Any` and no `dict` in a service signature.** If you reach for one, the schema is
  missing — write it.
- **Serialization lives in the model, not the method.** Aliases, `exclude_none`, CSV
  joining, enum values, epoch conversion: all of it is `Field(alias=...)`,
  `field_serializer`, or `model_config` on the schema. `Base` calls
  `model_dump(by_alias=True, exclude_none=True, mode="json")` once, uniformly. A method
  that builds a query string by hand is a bug.
- **No branching, no post-processing, no orchestration.** No `if` on the response, no
  reshaping, no merging two calls, no retry loop, no pagination loop. The method body is
  a single `return await self.<helper>(...)`. Cross-field preconditions belong in the
  request model's validator, not in an `if` at the top of the method.
- **The docstring carries `Args:`, `Returns:`, and the required Strava scope.**

The payoff is that a method is verifiable by reading it, and its test asserts four
values — endpoint, method, model, payload — with no behaviour to simulate.

#### The shapes, worked

**Path param + no input** — the scalar goes in the f-string, nothing else:

```python
async def get_activity_by_id(self, activity_id: int) -> DetailedActivity:
    return await self.fetch_data(
        endpoint=f"{self.base_url}/activities/{activity_id}",
        model=DetailedActivity,
    )
```

**Query params** — one model, even when it is only pagination. `GetActivitiesParams`
composes the shared `PaginationParams` and owns the epoch conversion for
`before`/`after`:

```python
async def get_logged_in_athlete_activities(
    self, params: GetActivitiesParams | None = None
) -> list[SummaryActivity]:
    return await self.fetch_data(
        endpoint=f"{self.base_url}/athlete/activities",
        model=list[SummaryActivity],
        params=params,
    )
```

Array responses are declared as `list[Model]`; `Base` validates through
`pydantic.TypeAdapter`, so bare models and generic aliases pass through the same path.
Give list-endpoint params a `None` default so the caller can take Strava's defaults.

**Path param + query params together:**

```python
async def get_activity_streams(
    self, activity_id: int, params: StreamParams
) -> StreamSet:
    return await self.fetch_data(
        endpoint=f"{self.base_url}/activities/{activity_id}/streams",
        model=StreamSet,
        params=params,
    )
```

`StreamParams` pins `key_by_type: Literal[True] = True` and serializes `keys` to CSV — the
method stays ignorant of both.

**Form-encoded write with a path param:**

```python
async def star_segment(self, segment_id: int, body: StarSegmentRequestBody) -> DetailedSegment:
    return await self._put_form(
        endpoint=f"{self.base_url}/segments/{segment_id}/starred",
        model=DetailedSegment,
        payload=body,
    )
```

A single-field body still gets a model. `starred: bool` as a loose argument is the thin
end of the wedge that ends in `**kwargs`.

**Multipart upload** — the file is a separate argument because it is a stream, not a
serializable field; everything else is still a model:

```python
async def create_upload(self, upload: CreateUploadRequestBody, file: BinaryIO) -> Upload:
    return await self._post_multipart(
        endpoint=f"{self.base_url}/uploads",
        model=Upload,
        payload=upload,
        file=file,
    )
```

**Non-JSON response** — the return type is the primitive, and there is no `model`:

```python
async def get_route_as_gpx(self, route_id: int) -> str:
    return await self._get_text(endpoint=f"{self.base_url}/routes/{route_id}/export_gpx")
```

#### What belongs elsewhere

| Temptation | Where it goes |
| --- | --- |
| "Fetch every page" | caller, or an explicit paginator helper — never hidden in a method |
| "Poll the upload until it finishes" | caller; `create_upload` returns the `Upload` and stops |
| "Reject `min_cat > max_cat`" | `model_validator` on `ExploreSegmentsParams` |
| "Convert a `datetime` to epoch seconds" | `field_serializer` on the params model |
| "Fall back to the summary model on 403" | nowhere — let the typed exception propagate |
| "Retry this one" | the retry predicate in `services/base.py` |

### Auth

Strava uses OAuth 2.0 **authorization code with refresh tokens**, not client
credentials:

- Authorization URL: `https://www.strava.com/api/v3/oauth/authorize`
- Token URL: `https://www.strava.com/api/v3/oauth/token`

The library does not run the interactive authorization leg. It takes a stored
`refresh_token` plus `client_id`/`client_secret` from settings and exchanges it for a
short-lived access token (6 hours) at `POST /oauth/token` with
`grant_type=refresh_token`.

- Token refresh is guarded by an `asyncio.Lock` and cached with a conservative TTL
  (shorter than the returned `expires_at`) so concurrent callers never stampede.
- Strava may return a **new refresh token** on each exchange. Persist/propagate it —
  silently discarding it will strand the credential.
- `invalidate_token()` is called when a request fails with an auth error, so the next
  call re-fetches.
- The token endpoint takes the client secret in the body: pass `error_endpoint=` with a
  redacted URL so no secret reaches exception messages or logs.

**Scopes.** Every scope-gated endpoint documents its requirement in the swagger
`description`. Mirror it in the method docstring, because a missing scope surfaces as a
`401`/`403` at runtime, not at import time:

| Scope | Grants |
| --- | --- |
| `read` | public segments, routes, profile, posts, events, club feeds, leaderboards |
| `read_all` | private routes, segments, and events |
| `profile:read_all` | full profile regardless of visibility settings |
| `profile:write` | update weight/FTP, star and unstar segments |
| `activity:read` | activities visible to Everyone/Followers, no privacy-zone data |
| `activity:read_all` | plus privacy-zone data and "Only You" activities |
| `activity:write` | create manual activities and uploads, edit visible activities |

### Errors

- Single root exception (`StravaError`) with `message`, `status_code`, `endpoint`,
  `details`.
- Two branches: `StravaClientError` (4xx) and `StravaServerError` (5xx), plus
  `StravaConnectionError` for transport failures.
- `map_status_code_to_exception` maps specific statuses to specific exceptions and falls
  back by range so unmapped 4xx/5xx are still distinguishable. Add new specific
  exceptions there rather than in call sites.
- Statuses worth distinguishing for Strava: `401` (expired/invalid token → invalidate and
  retry once), `403` (missing scope or private resource → *not* retryable, do not churn
  the token), `404`, `429` (rate limit), `500`.

### Service registry and limits

`build_service_registry(config)` returns
`{name: ServiceConfig(cls, base_url, requests_per_second)}`. The client's
`_get_service(name, Type)` reads this registry, so adding a service is a registry entry
plus a property.

**Divergence from the generic multi-service shape:** every Strava service shares the one
base URL `https://www.strava.com/api/v3`, and the rate limit is **app-wide, not
per-service**. Do not give each service its own independent limiter — that would
multiply the effective request rate by the number of services and get the app throttled.
Keep one shared `AsyncLimiter` (or a small limiter object) on the client and hand the
same instance to every service via the registry.

**Rate limits.** Strava enforces two windows — a 15-minute window that resets on natural
quarter-hour boundaries, and a daily window that resets at midnight UTC — with separate
overall and read-only budgets. The concrete numbers are per-application and change; read
them from settings (env-overridable) instead of hardcoding, and check
https://developers.strava.com/docs/rate-limits when setting the defaults. Responses
carry `X-RateLimit-Limit` / `X-RateLimit-Usage` and `X-ReadRateLimit-Limit` /
`X-ReadRateLimit-Usage`; prefer reacting to those over guessing. A `429` does not
reliably carry `Retry-After`, so back off to the next quarter-hour boundary rather than
assuming the header exists.

## Endpoint Inventory

Nine services, from the swagger `tags`. Path prefix `/api/v3` is in the base URL.

| Service | Endpoints |
| --- | --- |
| activities | `POST /activities`, `GET|PUT /activities/{id}`, `GET /activities/{id}/{comments,kudos,laps,zones}`, `GET /athlete/activities` |
| athletes | `GET|PUT /athlete`, `GET /athlete/zones`, `GET /athletes/{id}/stats` |
| clubs | `GET /athlete/clubs`, `GET /clubs/{id}`, `GET /clubs/{id}/{activities,admins,members}` |
| gear | `GET /gear/{id}` |
| routes | `GET /athletes/{id}/routes`, `GET /routes/{id}`, `GET /routes/{id}/export_gpx`, `GET /routes/{id}/export_tcx` |
| segments | `GET /segments/{id}`, `GET /segments/explore`, `GET /segments/starred`, `PUT /segments/{id}/starred` |
| segment_efforts | `GET /segment_efforts`, `GET /segment_efforts/{id}` |
| streams | `GET /{activities,routes,segments,segment_efforts}/{id}/streams` |
| uploads | `POST /uploads`, `GET /uploads/{uploadId}` |

Parameter conventions to honour:

- **Pagination:** shared `page` (default 1) and `per_page` (default 30) query params on
  the eight list endpoints. Model them once in `schemas/params.py` and reuse.
- **Time filters:** `GET /athlete/activities` takes `before`/`after` as **epoch
  integers**; `GET /segment_efforts` takes `start_date_local`/`end_date_local` as **ISO
  8601 strings**. Do not unify them into one type by accident.
- **CSV arrays:** `bounds` on `/segments/explore` is exactly 4 floats
  (`sw_lat,sw_lng,ne_lat,ne_lng`), and `keys` on the stream endpoints is a CSV of the
  stream-type enum. Both serialize as comma-joined strings, not repeated params.
- **`key_by_type=true`** is required on every streams call. Default it in the method.
- **Enums:** `data_type` on uploads (`fit`, `fit.gz`, `tcx`, `tcx.gz`, `gpx`, `gpx.gz`),
  `activity_type` on explore (`running`, `riding`), stream keys, climbing category 0–5.
  Encode these as `Literal`/`StrEnum` so wrong values fail before the request.
- **Uploads are asynchronous:** `POST /uploads` returns an `Upload` with an `id` and a
  `status`; the caller polls `GET /uploads/{uploadId}` until `activity_id` or `error` is
  set. Do not build a blocking poll loop inside the service — return the `Upload` and let
  the caller decide.

## Schemas

The swagger `$ref`s point at external files (`https://developers.strava.com/swagger/
*.json`), so there are no inline definitions to codegen from — write the models by hand
from the response `examples` in `context/strava_swagger.json` and the published model
docs. Map one module per swagger file:

| Swagger file | `schemas/` module | Models |
| --- | --- | --- |
| `activity.json` | `activity_model.py` | `DetailedActivity`, `SummaryActivity`, `UpdatableActivity`, `ClubActivity` |
| `athlete.json` | `athlete_model.py` | `DetailedAthlete`, `SummaryAthlete`, `ClubAthlete` |
| `activity_stats.json` | `athlete_model.py` | `ActivityStats` |
| `club.json` | `club_model.py` | `DetailedClub`, `SummaryClub` |
| `comment.json`, `lap.json` | `activity_model.py` | `Comment`, `Lap` |
| `gear.json` | `gear_model.py` | `DetailedGear` |
| `route.json` | `route_model.py` | `Route` |
| `segment.json` | `segment_model.py` | `DetailedSegment`, `SummarySegment`, `ExplorerResponse` |
| `segment_effort.json` | `segment_effort_model.py` | `DetailedSegmentEffort` |
| `stream.json` | `stream_model.py` | `StreamSet` |
| `upload.json` | `upload_model.py` | `Upload` |
| `zones.json` | `zone_model.py` | `Zones`, `ActivityZone` |
| `fault.json` | `fault_model.py` | `Fault` (consumed by `exceptions.py` mapping code) |

Request-side models live alongside them, one per endpoint that takes structured input.
Name them for the endpoint, not the resource, so the pairing with a method is obvious:
`CreateActivityRequestBody`, `UpdateActivityRequestBody`, `UpdateAthleteRequestBody`,
`StarSegmentRequestBody`, `CreateUploadRequestBody`, and params models
`GetActivitiesParams`, `GetSegmentEffortsParams`, `ExploreSegmentsParams`,
`StreamParams`. `schemas/params.py` holds the shared `PaginationParams` (`page`,
`per_page`) that list-endpoint params models compose.

Because the service layer is declarative, these models carry all the wire behaviour:

- Set `model_config = ConfigDict(populate_by_name=True, extra="forbid")` on request
  models so a typo'd field fails at construction rather than being sent and ignored.
- Encode enums as `Literal`/`StrEnum` — `data_type`, `activity_type`, stream keys,
  climbing category 0–5 — so a wrong value never reaches the wire.
- Put cross-field rules in `model_validator`: `min_cat <= max_cat`, `bounds` being
  exactly four floats, `keys` being non-empty.
- Put wire-format conversion in `field_serializer`: CSV joining for `bounds` and `keys`,
  `datetime` → epoch seconds for `before`/`after`, `datetime` → ISO 8601 for
  `start_date_local`/`end_date_local`, `bool` → the `1`/`0` that Strava's form fields
  expect for `trainer` and `commute`.

Modelling notes:

- Strava returns `Summary*` or `Detailed*` for the same resource depending on scope and
  `resource_state`. Keep them as separate models; do not collapse them into one
  all-optional blob.
- `latlng` fields are two-element `[lat, lng]` arrays, not objects.
- Map polylines arrive as encoded strings — keep them as `str`; decoding is out of scope.
- Distances are metres, times are seconds, `start_date` is UTC and `start_date_local` is
  wall-clock in the activity's timezone. Do not "helpfully" convert.
- Nullable-everywhere is real: fields like `ftp`, `weight`, `external_id`, and
  `upload_id` come back `null` for many athletes. Default to `| None`.

## Change Patterns

### Adding a new endpoint to an existing service

1. Confirm the shape against `context/strava_swagger.json` first.
2. Add or update response models in `src/strava_async/schemas/<service>_model.py`.
3. Add the request-body / query-param model when the endpoint takes structured input —
   including its validators and serializers, since the method will carry none.
4. Add an async method to the service class: one `return await self.<helper>(...)`, path
   params in the f-string, everything else as models. See "Service methods are
   declarative" for the shape to copy.
5. Use `fetch_data` with an explicit model for JSON reads; use `_post_form`,
   `_post_multipart`, `_put_form`, `_delete`, `_get_text`, or `_get_bytes` otherwise.
6. Give the method a docstring with `Args:`, `Returns:`, and the **required Strava
   scope**.
7. Add/extend tests in `tests/test_<service>_service.py`.

### Adding a new service

1. Create the service class in `src/strava_async/services/` inheriting `Base`.
2. Register it in `registry.py` sharing the app-wide limiter and the v3 base URL.
3. Expose it as a property on the client in `client.py` via `_get_service`.
4. Add tests for lazy initialization, the registry entry, and each method.

(New base URLs only apply if Strava ships a surface outside `/api/v3` — add it to
`settings.py` if so.)

### Adding a new error type

1. Add the exception class to `exceptions.py` under the right branch.
2. Add the status code to `map_status_code_to_exception`.
3. If it should be retried, add it to the retry predicate in `services/base.py`.
4. Add a case to `tests/test_exceptions.py` and, if retried,
   `tests/test_base_service.py`.

## Testing Expectations

- pytest with pytest-asyncio for async methods.
- Service tests: patch `fetch_data` (or the relevant `Base` helper) with `AsyncMock` and
  assert the endpoint, method, model, and payload passed to it. Because methods are
  declarative, that call assertion *is* the test — there is no behaviour left to cover.
  Do not exercise real HTTP in service tests.
- Validation and serialization are tested on the schema, not through the service: a
  rejected `min_cat > max_cat`, a CSV-joined `bounds`, an epoch-converted `after`. If a
  service test needs to assert on transformed values, logic has leaked out of the model.
- Guard the declarative style in `tests/test_architecture.py`: assert that no public
  service method annotates a parameter or return as `dict`, `Any`, or an untyped
  container, and that non-path parameters are `BaseModel` subclasses.
- Pipeline tests live in `tests/test_base_service.py`: status→exception mapping, retry
  behaviour, 429 backoff, token refresh and invalidation, rate limiting, redacted
  endpoints.
- Schema tests cover alias handling, optional fields, and `exclude_none` / `by_alias`
  serialization of request bodies. Use the `examples` blocks in the swagger as fixtures —
  they are real Strava payloads.
- Test the serialization edge cases explicitly: CSV `bounds` and stream `keys`, epoch vs
  ISO date params, form-encoding of writes.
- Architecture tests (`tests/test_architecture.py`) parse the AST of every source file and
  assert the import boundaries above. They include discovery guards that fail loudly if
  the source tree moves. Extend the rules when you add a layer.
- Keep tests deterministic and offline by default — no network, no sleeps, no clock
  dependence.

## Style and Quality

- Fully typed and async-first. No blocking I/O in async paths.
- The service layer is declarative: Pydantic in, Pydantic out, one delegating call per
  method. Validation and serialization belong to the schema; transport belongs to `Base`.
  A service method that contains logic is in the wrong layer.
- Use `Protocol` types for injected collaborators so layers stay decoupled and testable.
- Secrets (`client_secret`, `refresh_token`, access tokens) are `SecretStr` in settings,
  never logged, never interpolated into an error message or endpoint string.
- Reuse existing patterns for service methods and model validation rather than inventing a
  second way to do the same thing.
- Public API changes are intentional and reflected in tests.

## Notes for Agents

- Before editing, read the related service and its tests to preserve project patterns.
- Check `context/strava_swagger.json` before trusting memory about a Strava endpoint —
  parameter names and enums there are authoritative.
- Prefer minimal, focused changes over broad refactors.
- If you change behavior, update or add tests in the same change.
- Run `uv run pytest`, `uv run ruff check --fix`, `uv run ruff format`, and
  `uv run ty check` before concluding work.
- If a change requires crossing an architectural boundary, that is a signal the design is
  wrong — raise it rather than weakening `tests/test_architecture.py`.
