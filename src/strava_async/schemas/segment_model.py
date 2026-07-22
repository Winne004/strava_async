"""Segments and the segment explorer."""

from datetime import date, datetime

from pydantic import Field

from strava_async.schemas.base import RequestModel, ResponseModel
from strava_async.schemas.common import LatLng, PolylineMap

__all__ = [
    "AthleteSegmentStats",
    "DetailedSegment",
    "ExplorerResponse",
    "ExplorerSegment",
    "StarSegmentRequestBody",
    "SummarySegment",
]


class AthleteSegmentStats(ResponseModel):
    """The authenticated athlete's history on a segment."""

    pr_elapsed_time: int | None = None
    pr_date: date | None = None
    effort_count: int | None = None


class SummarySegment(ResponseModel):
    """A segment as embedded in an effort or listed."""

    id: int
    resource_state: int | None = None
    name: str | None = None
    activity_type: str | None = None
    distance: float | None = None
    average_grade: float | None = None
    maximum_grade: float | None = None
    elevation_high: float | None = None
    elevation_low: float | None = None
    start_latlng: LatLng | None = None
    end_latlng: LatLng | None = None
    climb_category: int | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    private: bool | None = None
    hazardous: bool | None = None
    starred: bool | None = None


class DetailedSegment(SummarySegment):
    """A segment fetched on its own."""

    created_at: datetime | None = None
    updated_at: datetime | None = None
    total_elevation_gain: float | None = None
    map: PolylineMap | None = None
    effort_count: int | None = None
    athlete_count: int | None = None
    star_count: int | None = None
    athlete_segment_stats: AthleteSegmentStats | None = None


class ExplorerSegment(ResponseModel):
    """A segment as returned by the explorer, which has its own field names."""

    id: int
    resource_state: int | None = None
    name: str | None = None
    climb_category: int | None = None
    climb_category_desc: str | None = None
    avg_grade: float | None = None
    start_latlng: LatLng | None = None
    end_latlng: LatLng | None = None
    elev_difference: float | None = None
    distance: float | None = None
    points: str | None = None
    starred: bool | None = None


class ExplorerResponse(ResponseModel):
    """The explorer's envelope around its ten results."""

    segments: list[ExplorerSegment] = Field(default_factory=list)


class StarSegmentRequestBody(RequestModel):
    """Body for ``PUT /segments/{id}/starred``. Requires ``profile:write`` scope."""

    starred: bool
