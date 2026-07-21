"""Shared fixtures and test doubles.

Everything here is offline and clock-free: no network, no real sleeps, no dependence on
what time it happens to be.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Self

import pytest

from strava_async.services.base import Base

BASE_URL = "https://api.test/v3"
FIXED_NOW = datetime(2026, 7, 21, 10, 3, 0, tzinfo=UTC)


class FakeAuthClient:
    """Records what the pipeline asks of an auth client."""

    def __init__(self) -> None:
        self.header_calls = 0
        self.invalidations = 0

    async def get_headers(self) -> dict[str, str]:
        self.header_calls += 1
        return {"Authorization": "Bearer test-token"}

    def invalidate_token(self) -> None:
        self.invalidations += 1


class FakeLimiter:
    """Stands in for AsyncLimiter, counting acquisitions instead of pacing them."""

    def __init__(self) -> None:
        self.acquisitions = 0

    async def __aenter__(self) -> Self:
        self.acquisitions += 1
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class FakeResponse:
    """A stand-in for aiohttp's response object."""

    def __init__(
        self,
        *,
        status: int = 200,
        json_body: Any = None,
        text_body: str = "",
        bytes_body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._json_body = json_body
        self._text_body = text_body
        self._bytes_body = bytes_body
        self.headers = headers or {}

    async def json(self, content_type: str | None = None) -> Any:
        return self._json_body

    async def text(self) -> str:
        return self._text_body

    async def read(self) -> bytes:
        return self._bytes_body


class _ResponseContext:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self._response = response

    async def __aenter__(self) -> FakeResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class FakeSession:
    """Serves a scripted queue of responses and records every request made.

    A queued ``Exception`` is raised on entering the context, which is how transport
    failures are simulated.
    """

    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _ResponseContext:
        self.requests.append({"method": method, "url": url, **kwargs})
        if not self._responses:
            raise AssertionError(f"Unexpected extra request: {method} {url}")
        return _ResponseContext(self._responses.pop(0))

    @property
    def last_request(self) -> dict[str, Any]:
        return self.requests[-1]


class SleepRecorder:
    """Captures the backoff the pipeline computes without spending it."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


@pytest.fixture
def auth_client() -> FakeAuthClient:
    return FakeAuthClient()


@pytest.fixture
def limiter() -> FakeLimiter:
    return FakeLimiter()


@pytest.fixture
def sleeper() -> SleepRecorder:
    return SleepRecorder()


@pytest.fixture
def make_base(
    auth_client: FakeAuthClient, limiter: FakeLimiter, sleeper: SleepRecorder
) -> Callable[..., Base]:
    """Build a ``Base`` bound to a scripted session."""

    def factory(session: FakeSession, **kwargs: Any) -> Base:
        options: dict[str, Any] = {
            "max_retry_attempts": 3,
            "max_retry_wait_seconds": 60.0,
            "sleep": sleeper,
            "now": lambda: FIXED_NOW,
        }
        options.update(kwargs)
        return Base(session, BASE_URL, auth_client, limiter, **options)  # ty: ignore[invalid-argument-type]

    return factory


@pytest.fixture
def make_service(auth_client: FakeAuthClient, limiter: FakeLimiter) -> Callable[[type[Base]], Any]:
    """Build a service with a session that would fail loudly if it were ever used."""

    def factory(service_class: type[Base]) -> Any:
        return service_class(None, BASE_URL, auth_client, limiter)  # ty: ignore[invalid-argument-type]

    return factory
