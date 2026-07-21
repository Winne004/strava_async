"""Routes — planned lines, as opposed to activities, which were ridden or run."""

from datetime import datetime

from pydantic import Field

from strava_async.schemas.athlete_model import SummaryAthlete
from strava_async.schemas.base import ResponseModel
from strava_async.schemas.common import LatLng, PolylineMap
from strava_async.schemas.segment_model import SummarySegment

__all__ = ["Route", "Waypoint"]


class Waypoint(ResponseModel):
    """A point of interest along a route."""

    latlng: LatLng | None = None
    target_latlng: LatLng | None = None
    categories: list[str] = Field(default_factory=list)
    title: str | None = None
    description: str | None = None
    distance_into_route: int | None = None


class Route(ResponseModel):
    """A saved route.

    ``type`` is 1 for a ride and 2 for a run; ``sub_type`` is 1 road, 2 mountain bike,
    3 cross, 4 trail, 5 mixed.
    """

    id: int | None = None
    id_str: str | None = None
    resource_state: int | None = None
    name: str | None = None
    description: str | None = None
    athlete: SummaryAthlete | None = None
    distance: float | None = None
    elevation_gain: float | None = None
    map: PolylineMap | None = None
    type: int | None = None
    sub_type: int | None = None
    private: bool | None = None
    starred: bool | None = None
    timestamp: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    estimated_moving_time: int | None = None
    segments: list[SummarySegment] = Field(default_factory=list)
    waypoints: list[Waypoint] = Field(default_factory=list)
