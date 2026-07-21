"""SegmentEffortsService delegates each endpoint correctly."""

from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.params import GetSegmentEffortsParams
from strava_async.schemas.segment_effort_model import DetailedSegmentEffort
from strava_async.services.segment_efforts import SegmentEffortsService
from tests.conftest import BASE_URL

SENTINEL = object()


def service(make_service: Any) -> tuple[SegmentEffortsService, AsyncMock]:
    instance = make_service(SegmentEffortsService)
    mock = AsyncMock(return_value=SENTINEL)
    instance.fetch_data = mock
    return instance, mock


async def test_get_efforts_by_segment_id(make_service: Any) -> None:
    """The segment is a query parameter here, not a path segment."""
    instance, mock = service(make_service)
    params = GetSegmentEffortsParams(segment_id=788127, per_page=20)

    assert await instance.get_efforts_by_segment_id(params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/segment_efforts",
        model=list[DetailedSegmentEffort],
        params=params,
    )


async def test_get_segment_effort_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_segment_effort_by_id(1234556789) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/segment_efforts/1234556789", model=DetailedSegmentEffort
    )
