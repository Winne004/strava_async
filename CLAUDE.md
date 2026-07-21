CLAUDE.md
Repository guidance for AI coding agents and contributors working on <package_name>.

Template notes (delete this block once filled in): Replace <package_name>, <Vendor>, <VendorClient>, <ServiceA>, <AuthClient> etc. throughout. This template describes an async, multi-service HTTP API client: one client object, N lazily-created service objects, a shared base class that owns the request pipeline (auth, rate limiting, retries, error mapping, response validation), and Pydantic models for every request/response shape.

Project Summary
Package: <package_name>
Purpose: async Python client for <Vendor> APIs (<ServiceA>, <ServiceB>, <ServiceC>, ...)
Python: >=3.13
Package manager: uv only
Core stack: aiohttp, pydantic, pydantic-settings, aiolimiter, tenacity
Mandatory Tooling Rules
Use uv exclusively for dependency management and command execution.
Never use pip, poetry, or conda directly in this repo.
Common commands:

Install/sync env: uv sync
Add runtime dependency: uv add <package>
Add dev dependency: uv add --group dev <package>
Remove dependency: uv remove <package>
Re-lock dependencies: uv lock
Run tools with uv run:

Tests: uv run pytest
Lint: uv run ruff check --fix
Format: uv run ruff format
Type check: uv run ty check
Pre-commit (all files): uv run pre-commit run --all-files
Local Development
Sync environment:
uv sync
Set credentials for local integration use:
export CLIENT_ID="..."
export CLIENT_SECRET="..." (These are read by pydantic-settings in settings.py; names must match the settings field names, case-insensitively.)
Run tests and quality checks before finishing changes:
uv run pytest
uv run ruff check --fix
uv run ruff format
uv run ty check
Repository Layout
src/<package_name>/
  client.py        # main async client / context manager, lazy service properties
  initialise.py    # factory: builds settings, registry, auth client, and the client
  settings.py      # pydantic-settings: credentials + per-service base URLs
  registry.py      # service name -> (class, base_url, rate limit)
  protocols.py     # structural types (e.g. AuthClientProtocol) — no internal imports
  exceptions.py    # exception hierarchy + HTTP status -> exception mapping
  auth/            # token acquisition, caching, invalidation
  services/
    base.py        # Base: the whole request pipeline lives here
    <service>.py   # one module per API surface, thin methods over Base helpers
  schemas/         # Pydantic models: responses, request bodies, query params
tests/             # pytest suite, mirrors the src layout
Architecture Notes
Layering (enforced by tests — see Architecture Tests below)
settings / protocols / exceptions / auth   <- foundation: no internal imports at all
schemas                                    <- may import stdlib + pydantic only
services/base.py                           <- imports protocols + exceptions only
services/<service>.py                      <- imports base + schemas + protocols
registry.py                                <- imports services + settings
client.py                                  <- imports services + registry + protocols
initialise.py                              <- imports everything; the only wiring point
Rules of thumb:

Dependencies point downward only. A lower layer never imports a higher one.
client.py must not import settings or the concrete auth client — it receives a registry and an auth class (typed via protocols.py) so it stays substitutable.
Domain services never import client, registry, settings, or the auth module.
services/base.py never imports a sibling service or any schema.
Client lifecycle
Construct with initialise_<vendor>_client() — never by hand in application code.
Always use the client as an async context manager:
async with initialise_<vendor>_client() as client:
    result = await client.<service>.<method>(...)
__aenter__ creates the aiohttp.ClientSession (with a bounded TCPConnector) unless an external session was injected; __aexit__ closes it only if the client owns it, then clears cached services and the auth client.
The auth client and each service are lazily created on first access and cached for the lifetime of the context. Accessing them outside the context raises RuntimeError.
Request pipeline
All network I/O funnels through Base in services/base.py:

Acquire auth headers (skipped when the caller passes explicit headers — e.g. a different auth mechanism such as an API/policy key).
Acquire a slot from the per-service AsyncLimiter (rate limiting).
Issue the request with aiohttp.
_raise_for_status maps the HTTP status to a typed exception, attaching status_code, endpoint, and the response body in details. 429 also carries retry_after parsed from the Retry-After header.
tenacity retries transient failures (connection errors, auth errors, 429) with Retry-After honoured when present, exponential backoff otherwise.
For JSON endpoints, the body is validated into the caller-supplied Pydantic model.
Base exposes:

Helper	Use for
fetch_data	JSON request/response pairs, validated against a model
_delete	DELETE with no response body
_get_text	text/plain responses
_put_text	text/plain request bodies
_put_empty	PUT with no body
_get_bytes	binary responses (images, downloads)
fetch_data is strictly for JSON in / validated JSON out. For anything else use the helper above — never bypass them with a raw self._session.request(...), or you lose rate limiting, retries, and error mapping.

Auth
Token fetch is guarded by an asyncio.Lock and cached with a conservative TTL (shorter than the server's actual expiry) so concurrent callers never stampede.
invalidate_token() is called when a request authenticated with the shared token fails with an auth error, so the next call re-fetches.
Requests that use a different auth mechanism pass uses_oauth=False (or explicit headers) so a 401 there never churns the shared token.
When an endpoint URL embeds a secret, pass error_endpoint= with a redacted URL so the secret never reaches exception messages or logs.
Errors
Single root exception (<Vendor>Error) with message, status_code, endpoint, details.
Two branches: <Vendor>ClientError (4xx) and <Vendor>ServerError (5xx), plus <Vendor>ConnectionError for transport failures.
map_status_code_to_exception maps specific statuses to specific exceptions and falls back by range so unmapped 4xx/5xx are still distinguishable. Add new specific exceptions there rather than in call sites.
Service registry and limits
build_service_registry(config) returns {name: ServiceConfig(cls, base_url, requests_per_second)}. Base URLs come from settings (env-overridable); rate limits are per service and reflect the vendor's documented quotas. The client's _get_service(name, Type) reads this registry, so adding a service is a registry entry plus a property.

Change Patterns
Adding a new endpoint to an existing service
Add or update response models in src/<package_name>/schemas/<service>_model.py.
Add request-body / query-param models (schemas/params.py or the service's model module) when the endpoint takes structured input.
Add an async method to the service class. Keep it thin: build the URL from self.base_url, validate cross-field preconditions, delegate to a Base helper.
Use fetch_data with an explicit model for JSON endpoints; use _delete, _get_text, _put_text, _put_empty, or _get_bytes otherwise.
Give the method a docstring with Args: and Returns:.
Add/extend tests in tests/test_<service>_service.py.
Adding a new service
Create the service class in src/<package_name>/services/ inheriting Base.
Add its base URL to settings.py.
Register it in registry.py with a suitable requests-per-second limit.
Expose it as a property on the client in client.py via _get_service.
Add tests for lazy initialization, the registry entry, and each method.
Adding a new error type
Add the exception class to exceptions.py under the right branch.
Add the status code to map_status_code_to_exception.
If it should be retried, add it to the retry predicate in services/base.py.
Add a case to tests/test_exceptions.py and, if retried, tests/test_base_service.py.
Testing Expectations
pytest with pytest-asyncio for async methods.
Service tests: patch fetch_data (or the relevant Base helper) with AsyncMock and assert the endpoint, method, model, and payload passed to it. Do not exercise real HTTP in service tests.
Pipeline tests live in tests/test_base_service.py: status→exception mapping, retry behaviour, Retry-After handling, token invalidation, rate limiting, redacted endpoints.
Schema tests cover alias handling, optional fields, and exclude_none / by_alias serialization behaviour of request bodies.
Architecture tests (tests/test_architecture.py) parse the AST of every source file and assert the import boundaries listed above. They include discovery guards that fail loudly if the source tree moves. Extend the rules when you add a layer.
Keep tests deterministic and offline by default — no network, no sleeps, no clock dependence.
Style and Quality
Fully typed and async-first. No blocking I/O in async paths.
Use Protocol types for injected collaborators so layers stay decoupled and testable.
Secrets are SecretStr in settings and never logged, never interpolated into an error message or endpoint string.
Reuse existing patterns for service methods and model validation rather than inventing a second way to do the same thing.
Public API changes are intentional and reflected in tests.
Notes for Agents
Before editing, read the related service and its tests to preserve project patterns.
Prefer minimal, focused changes over broad refactors.
If you change behavior, update or add tests in the same change.
Run uv run pytest, uv run ruff check --fix, uv run ruff format, and uv run ty check before concluding work.
If a change requires crossing an architectural boundary, that is a signal the design is wrong — raise it rather than weakening tests/test_architecture.py.