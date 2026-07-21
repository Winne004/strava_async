"""AthletesService delegates each endpoint correctly."""

from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.athlete_model import (
    ActivityStats,
    DetailedAthlete,
    UpdateAthleteRequestBody,
    Zones,
)
from strava_async.services.athletes import AthletesService
from tests.conftest import BASE_URL

SENTINEL = object()


def service(make_service: Any, helper: str = "fetch_data") -> tuple[AthletesService, AsyncMock]:
    instance = make_service(AthletesService)
    mock = AsyncMock(return_value=SENTINEL)
    setattr(instance, helper, mock)
    return instance, mock


async def test_get_logged_in_athlete(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_logged_in_athlete() is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/athlete", model=DetailedAthlete)


async def test_update_logged_in_athlete_puts_a_form(make_service: Any) -> None:
    """The swagger calls weight a path parameter; Strava takes it as a form field."""
    instance, mock = service(make_service, "_put_form")
    body = UpdateAthleteRequestBody(weight=72.5)

    assert await instance.update_logged_in_athlete(body) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/athlete", model=DetailedAthlete, payload=body
    )


async def test_get_logged_in_athlete_zones(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_logged_in_athlete_zones() is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/athlete/zones", model=Zones)


async def test_get_stats(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_stats(134815) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/athletes/134815/stats", model=ActivityStats)
