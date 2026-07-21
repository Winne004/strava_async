"""ClubsService delegates each endpoint correctly."""

from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.athlete_model import ClubAthlete, SummaryAthlete
from strava_async.schemas.club_model import ClubActivity, DetailedClub, SummaryClub
from strava_async.schemas.params import PaginationParams
from strava_async.services.clubs import ClubsService
from tests.conftest import BASE_URL

SENTINEL = object()
PARAMS = PaginationParams(page=2, per_page=10)


def service(make_service: Any) -> tuple[ClubsService, AsyncMock]:
    instance = make_service(ClubsService)
    mock = AsyncMock(return_value=SENTINEL)
    instance.fetch_data = mock
    return instance, mock


async def test_get_logged_in_athlete_clubs(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_logged_in_athlete_clubs(PARAMS) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/athlete/clubs", model=list[SummaryClub], params=PARAMS
    )


async def test_get_club_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_club_by_id(1) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/clubs/1", model=DetailedClub)


async def test_get_club_activities_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_club_activities_by_id(1, PARAMS) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/clubs/1/activities", model=list[ClubActivity], params=PARAMS
    )


async def test_get_club_admins_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_club_admins_by_id(1, PARAMS) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/clubs/1/admins", model=list[SummaryAthlete], params=PARAMS
    )


async def test_get_club_members_by_id(make_service: Any) -> None:
    """Members carry club standing, admins do not — different models, same shape of call."""
    instance, mock = service(make_service)

    assert await instance.get_club_members_by_id(1, PARAMS) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/clubs/1/members", model=list[ClubAthlete], params=PARAMS
    )
