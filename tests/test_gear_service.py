"""GearService delegates its one endpoint correctly."""

from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.gear_model import DetailedGear
from strava_async.services.gear import GearService
from tests.conftest import BASE_URL

SENTINEL = object()


async def test_get_gear_by_id(make_service: Any) -> None:
    """Gear identifiers are prefixed strings, not integers."""
    instance = make_service(GearService)
    mock = AsyncMock(return_value=SENTINEL)
    instance.fetch_data = mock

    assert await instance.get_gear_by_id("b1231") is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/gear/b1231", model=DetailedGear)
