"""StreamsService delegates each endpoint correctly."""

from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.params import StreamParams
from strava_async.schemas.stream_model import StreamSet
from strava_async.services.streams import StreamsService
from tests.conftest import BASE_URL

SENTINEL = object()
PARAMS = StreamParams(keys=["time", "heartrate"])


def service(make_service: Any) -> tuple[StreamsService, AsyncMock]:
    instance = make_service(StreamsService)
    mock = AsyncMock(return_value=SENTINEL)
    instance.fetch_data = mock
    return instance, mock


async def test_get_activity_streams(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_activity_streams(7, PARAMS) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/activities/7/streams", model=StreamSet, params=PARAMS
    )


async def test_get_segment_streams(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_segment_streams(229781, PARAMS) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/segments/229781/streams", model=StreamSet, params=PARAMS
    )


async def test_get_segment_effort_streams(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_segment_effort_streams(42, PARAMS) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/segment_efforts/42/streams", model=StreamSet, params=PARAMS
    )


async def test_get_route_streams_takes_no_keys(make_service: Any) -> None:
    """Alone among the four, this endpoint has no `keys` parameter."""
    instance, mock = service(make_service)

    assert await instance.get_route_streams(42) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/routes/42/streams", model=StreamSet)


def test_stream_params_pin_key_by_type() -> None:
    """key_by_type=true is what makes the response an object keyed by stream type."""
    assert PARAMS.key_by_type is True
