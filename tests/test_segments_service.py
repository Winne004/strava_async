"""SegmentsService delegates each endpoint correctly."""

from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.params import ExploreSegmentsParams, PaginationParams
from strava_async.schemas.segment_model import (
    DetailedSegment,
    ExplorerResponse,
    StarSegmentRequestBody,
    SummarySegment,
)
from strava_async.services.segments import SegmentsService
from tests.conftest import BASE_URL

SENTINEL = object()


def service(make_service: Any, helper: str = "fetch_data") -> tuple[SegmentsService, AsyncMock]:
    instance = make_service(SegmentsService)
    mock = AsyncMock(return_value=SENTINEL)
    setattr(instance, helper, mock)
    return instance, mock


async def test_get_segment_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_segment_by_id(229781) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/segments/229781", model=DetailedSegment)


async def test_explore_segments(make_service: Any) -> None:
    instance, mock = service(make_service)
    params = ExploreSegmentsParams(bounds=[37.8, -122.5, 37.9, -122.4], activity_type="riding")

    assert await instance.explore_segments(params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/segments/explore", model=ExplorerResponse, params=params
    )


async def test_get_starred_segments(make_service: Any) -> None:
    instance, mock = service(make_service)
    params = PaginationParams(page=1)

    assert await instance.get_logged_in_athlete_starred_segments(params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/segments/starred", model=list[SummarySegment], params=params
    )


async def test_star_segment_puts_a_form(make_service: Any) -> None:
    instance, mock = service(make_service, "_put_form")
    body = StarSegmentRequestBody(starred=True)

    assert await instance.star_segment(229781, body) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/segments/229781/starred",
        model=DetailedSegment,
        payload=body,
    )
