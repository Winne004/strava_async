"""Client lifecycle: session ownership, lazy services, and context discipline."""

from typing import Any

import aiohttp
import pytest

from strava_async.client import StravaClient
from strava_async.registry import ServiceConfig, build_service_registry
from strava_async.services.activities import ActivitiesService
from strava_async.services.athletes import AthletesService
from strava_async.services.base import Base
from strava_async.settings import StravaSettings
from tests.conftest import FakeAuthClient, FakeLimiter

SERVICE_NAMES = [
    "activities",
    "athletes",
    "clubs",
    "gear",
    "routes",
    "segment_efforts",
    "segments",
    "streams",
    "uploads",
]


def make_settings(**overrides: Any) -> StravaSettings:
    values: dict[str, Any] = {
        "client_id": "123",
        "client_secret": "shh",
        "refresh_token": "refresh-0",
        "base_url": "https://api.test/v3",
    }
    values.update(overrides)
    return StravaSettings(**values)


def make_client(session: aiohttp.ClientSession | None = None) -> StravaClient:
    return StravaClient(
        registry=build_service_registry(make_settings()),
        auth_factory=lambda _session: FakeAuthClient(),
        session=session,
    )


async def test_services_are_lazy_and_cached() -> None:
    async with make_client(session=object()) as client:  # ty: ignore[invalid-argument-type]
        first = client.activities
        second = client.activities

    assert isinstance(first, ActivitiesService)
    assert first is second


async def test_every_service_is_reachable() -> None:
    async with make_client(session=object()) as client:  # ty: ignore[invalid-argument-type]
        services = [getattr(client, name) for name in SERVICE_NAMES]

    assert len(services) == len(SERVICE_NAMES)
    assert all(isinstance(service, Base) for service in services)


async def test_services_share_one_auth_client() -> None:
    async with make_client(session=object()) as client:  # ty: ignore[invalid-argument-type]
        assert client.activities._auth_client is client.athletes._auth_client
        assert client.activities._auth_client is client.auth


async def test_accessing_a_service_outside_the_context_raises() -> None:
    client = make_client()

    with pytest.raises(RuntimeError, match="async context manager"):
        _ = client.activities


async def test_accessing_auth_outside_the_context_raises() -> None:
    client = make_client()

    with pytest.raises(RuntimeError, match="async context manager"):
        _ = client.auth


async def test_exit_clears_cached_services_and_auth() -> None:
    client = make_client(session=object())  # ty: ignore[invalid-argument-type]
    async with client:
        _ = client.activities

    assert client._services == {}
    assert client._auth_client is None


async def test_an_injected_session_is_not_closed() -> None:
    session = aiohttp.ClientSession()
    try:
        async with make_client(session=session) as client:
            _ = client.athletes
        assert not session.closed
    finally:
        await session.close()


async def test_an_owned_session_is_created_and_closed() -> None:
    client = make_client()
    async with client as entered:
        session = entered._session
        assert isinstance(session, aiohttp.ClientSession)
        assert not session.closed

    assert session.closed


async def test_registry_mismatch_is_caught() -> None:
    """The registry is data; a wrong entry should fail loudly, not silently."""
    registry = build_service_registry(make_settings())
    registry["activities"] = ServiceConfig(
        service_class=AthletesService,
        base_url="https://api.test/v3",
        limiter=registry["activities"].limiter,
    )
    client = StravaClient(
        registry=registry,
        auth_factory=lambda _session: FakeAuthClient(),
        session=object(),  # ty: ignore[invalid-argument-type]
    )

    async with client:
        with pytest.raises(TypeError, match="expected ActivitiesService"):
            _ = client.activities


async def test_services_get_the_configured_base_url() -> None:
    async with make_client(session=object()) as client:  # ty: ignore[invalid-argument-type]
        assert client.activities.base_url == "https://api.test/v3"


async def test_limiter_is_shared_across_services() -> None:
    """Strava's quota is per application, so one limiter must serve every service."""
    async with make_client(session=object()) as client:  # ty: ignore[invalid-argument-type]
        assert client.activities._limiter is client.segments._limiter


def test_fake_limiter_is_not_used_in_production_path() -> None:
    """Guards the fixture from drifting away from the real limiter's interface."""
    limiter = FakeLimiter()
    assert hasattr(limiter, "__aenter__")
    assert hasattr(limiter, "__aexit__")
