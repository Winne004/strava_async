"""ActivitiesService delegates each endpoint correctly."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.activity_model import (
    Comment,
    CreateActivityRequestBody,
    DetailedActivity,
    Lap,
    SummaryActivity,
    UpdateActivityRequestBody,
)
from strava_async.schemas.athlete_model import SummaryAthlete
from strava_async.schemas.params import (
    GetActivitiesParams,
    GetActivityParams,
    GetCommentsParams,
    PaginationParams,
)
from strava_async.schemas.zone_model import ActivityZone
from strava_async.services.activities import ActivitiesService
from tests.conftest import BASE_URL

SENTINEL = object()


def service(make_service: Any, helper: str = "fetch_data") -> tuple[ActivitiesService, AsyncMock]:
    instance = make_service(ActivitiesService)
    mock = AsyncMock(return_value=SENTINEL)
    setattr(instance, helper, mock)
    return instance, mock


async def test_create_activity_posts_a_form(make_service: Any) -> None:
    instance, mock = service(make_service, "_post_form")
    body = CreateActivityRequestBody(
        name="Chill Day",
        sport_type="Ride",
        start_date_local=datetime(2026, 2, 20, 10),
        elapsed_time=100,
    )

    assert await instance.create_activity(body) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/activities", model=DetailedActivity, payload=body
    )


async def test_get_activity_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)
    params = GetActivityParams(include_all_efforts=True)

    assert await instance.get_activity_by_id(7, params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/activities/7", model=DetailedActivity, params=params
    )


async def test_get_activity_by_id_without_params(make_service: Any) -> None:
    instance, mock = service(make_service)

    await instance.get_activity_by_id(7)

    assert mock.await_args is not None
    assert mock.await_args.kwargs["params"] is None


async def test_update_activity_sends_a_json_body(make_service: Any) -> None:
    """This is the one write in the API that takes JSON rather than form fields."""
    instance, mock = service(make_service)
    body = UpdateActivityRequestBody(name="Renamed")

    assert await instance.update_activity_by_id(7, body) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/activities/7",
        model=DetailedActivity,
        method="PUT",
        payload=body,
    )


async def test_get_logged_in_athlete_activities(make_service: Any) -> None:
    instance, mock = service(make_service)
    params = GetActivitiesParams(per_page=50)

    assert await instance.get_logged_in_athlete_activities(params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/athlete/activities",
        model=list[SummaryActivity],
        params=params,
    )


async def test_get_comments_by_activity_id(make_service: Any) -> None:
    instance, mock = service(make_service)
    params = GetCommentsParams(page_size=10)

    assert await instance.get_comments_by_activity_id(7, params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/activities/7/comments", model=list[Comment], params=params
    )


async def test_get_kudoers_by_activity_id(make_service: Any) -> None:
    instance, mock = service(make_service)
    params = PaginationParams(page=2)

    assert await instance.get_kudoers_by_activity_id(7, params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/activities/7/kudos",
        model=list[SummaryAthlete],
        params=params,
    )


async def test_get_laps_by_activity_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_laps_by_activity_id(7) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/activities/7/laps", model=list[Lap])


async def test_get_zones_by_activity_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_zones_by_activity_id(7) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/activities/7/zones", model=list[ActivityZone]
    )
