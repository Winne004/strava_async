"""RoutesService delegates each endpoint correctly."""

from typing import Any
from unittest.mock import AsyncMock

from strava_async.schemas.params import PaginationParams
from strava_async.schemas.route_model import Route
from strava_async.services.routes import RoutesService
from tests.conftest import BASE_URL

SENTINEL = object()


def service(make_service: Any, helper: str = "fetch_data") -> tuple[RoutesService, AsyncMock]:
    instance = make_service(RoutesService)
    mock = AsyncMock(return_value=SENTINEL)
    setattr(instance, helper, mock)
    return instance, mock


async def test_get_routes_by_athlete_id(make_service: Any) -> None:
    instance, mock = service(make_service)
    params = PaginationParams(per_page=10)

    assert await instance.get_routes_by_athlete_id(134815, params) is SENTINEL
    mock.assert_awaited_once_with(
        endpoint=f"{BASE_URL}/athletes/134815/routes", model=list[Route], params=params
    )


async def test_get_route_by_id(make_service: Any) -> None:
    instance, mock = service(make_service)

    assert await instance.get_route_by_id(42) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/routes/42", model=Route)


async def test_get_route_as_gpx_uses_the_text_helper(make_service: Any) -> None:
    """The exports are XML, not JSON, so they must not go through fetch_data."""
    instance, mock = service(make_service, "_get_text")

    assert await instance.get_route_as_gpx(42) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/routes/42/export_gpx")


async def test_get_route_as_tcx_uses_the_text_helper(make_service: Any) -> None:
    instance, mock = service(make_service, "_get_text")

    assert await instance.get_route_as_tcx(42) is SENTINEL
    mock.assert_awaited_once_with(endpoint=f"{BASE_URL}/routes/42/export_tcx")
