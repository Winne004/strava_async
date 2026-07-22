"""The service registry."""

from typing import Any

from strava_async.rate_limit import CompositeLimiter
from strava_async.registry import build_service_registry
from strava_async.services.activities import ActivitiesService
from strava_async.services.base import Base
from strava_async.settings import StravaSettings

EXPECTED_SERVICES = {
    "activities",
    "athletes",
    "clubs",
    "gear",
    "routes",
    "segment_efforts",
    "segments",
    "streams",
    "uploads",
}


def make_settings(**overrides: Any) -> StravaSettings:
    values: dict[str, Any] = {
        "client_id": "123",
        "client_secret": "shh",
        "refresh_token": "refresh-0",
    }
    values.update(overrides)
    return StravaSettings(**values)


def test_registers_every_service() -> None:
    assert set(build_service_registry(make_settings())) == EXPECTED_SERVICES


def test_every_entry_is_a_base_subclass() -> None:
    registry = build_service_registry(make_settings())

    assert all(issubclass(config.service_class, Base) for config in registry.values())


def test_all_services_share_one_limiter() -> None:
    """Strava's quota is per application. Per-service limiters would multiply the rate."""
    registry = build_service_registry(make_settings())
    limiters = {id(config.limiter) for config in registry.values()}

    assert len(limiters) == 1


def test_all_services_share_the_configured_base_url() -> None:
    registry = build_service_registry(make_settings(base_url="https://example.test/v3"))

    assert {config.base_url for config in registry.values()} == {"https://example.test/v3"}


def test_limiter_reflects_both_configured_budgets() -> None:
    """Strava budgets a short window and a daily one; both must be enforced."""
    registry = build_service_registry(
        make_settings(requests_per_quarter_hour=200, daily_request_limit=2000)
    )
    limiter = registry["activities"].limiter
    assert isinstance(limiter, CompositeLimiter)

    windows = [(inner.max_rate, inner.time_period) for inner in limiter.limiters]
    assert windows == [(200, 900), (2000, 86_400)]


def test_activities_maps_to_the_activities_service() -> None:
    assert build_service_registry(make_settings())["activities"].service_class is (
        ActivitiesService
    )


def test_requests_per_second_derives_from_the_window() -> None:
    assert make_settings(requests_per_quarter_hour=900).requests_per_second == 1.0
