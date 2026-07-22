"""Activities, their comments and laps, and the bodies that create or update them."""

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_serializer

from strava_async.schemas.athlete_model import SummaryAthlete
from strava_async.schemas.base import RequestModel, ResponseModel
from strava_async.schemas.common import LatLng, MetaActivity, MetaAthlete, PolylineMap
from strava_async.schemas.gear_model import SummaryGear
from strava_async.schemas.segment_effort_model import DetailedSegmentEffort

__all__ = [
    "Comment",
    "CreateActivityRequestBody",
    "DetailedActivity",
    "Lap",
    "Split",
    "SummaryActivity",
    "UpdateActivityRequestBody",
]


class SummaryActivity(ResponseModel):
    """An activity as listed.

    Distances are metres, times are seconds. ``start_date`` is UTC and
    ``start_date_local`` is wall-clock time in the activity's own timezone — they are
    different instants expressed the same way, so do not convert between them.
    """

    id: int
    resource_state: int | None = None
    external_id: str | None = None
    upload_id: int | None = None
    athlete: MetaAthlete | None = None
    name: str | None = None
    distance: float | None = None
    moving_time: int | None = None
    elapsed_time: int | None = None
    total_elevation_gain: float | None = None
    elev_high: float | None = None
    elev_low: float | None = None
    type: str | None = None
    sport_type: str | None = None
    workout_type: int | None = None
    start_date: datetime | None = None
    start_date_local: datetime | None = None
    timezone: str | None = None
    utc_offset: float | None = None
    start_latlng: LatLng | None = None
    end_latlng: LatLng | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_country: str | None = None
    achievement_count: int | None = None
    kudos_count: int | None = None
    comment_count: int | None = None
    athlete_count: int | None = None
    photo_count: int | None = None
    total_photo_count: int | None = None
    map: PolylineMap | None = None
    trainer: bool | None = None
    commute: bool | None = None
    manual: bool | None = None
    private: bool | None = None
    flagged: bool | None = None
    gear_id: str | None = None
    from_accepted_tag: bool | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    average_cadence: float | None = None
    average_temp: float | None = None
    average_watts: float | None = None
    weighted_average_watts: int | None = None
    kilojoules: float | None = None
    device_watts: bool | None = None
    max_watts: int | None = None
    has_heartrate: bool | None = None
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    device_name: str | None = None
    pr_count: int | None = None
    has_kudoed: bool | None = None
    suffer_score: int | None = None


class Split(ResponseModel):
    """One kilometre or mile of an activity."""

    distance: float | None = None
    elapsed_time: int | None = None
    elevation_difference: float | None = None
    moving_time: int | None = None
    split: int | None = None
    average_speed: float | None = None
    average_grade_adjusted_speed: float | None = None
    average_heartrate: float | None = None
    pace_zone: int | None = None


class Lap(ResponseModel):
    """A lap within an activity."""

    id: int
    resource_state: int | None = None
    name: str | None = None
    activity: MetaActivity | None = None
    athlete: MetaAthlete | None = None
    elapsed_time: int | None = None
    moving_time: int | None = None
    start_date: datetime | None = None
    start_date_local: datetime | None = None
    distance: float | None = None
    start_index: int | None = None
    end_index: int | None = None
    total_elevation_gain: float | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    average_cadence: float | None = None
    device_watts: bool | None = None
    average_watts: float | None = None
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    lap_index: int | None = None
    split: int | None = None
    pace_zone: int | None = None


class Comment(ResponseModel):
    """A comment on an activity.

    The embedded athlete is a first and last name only — there is no id to follow.
    """

    id: int
    activity_id: int | None = None
    post_id: int | None = None
    resource_state: int | None = None
    text: str | None = None
    mentions_metadata: dict[str, object] | None = None
    created_at: datetime | None = None
    athlete: SummaryAthlete | None = None
    cursor: str | None = None


class DetailedActivity(SummaryActivity):
    """An activity fetched on its own."""

    description: str | None = None
    calories: float | None = None
    embed_token: str | None = None
    device_name: str | None = None
    gear: SummaryGear | None = None
    segment_efforts: list[DetailedSegmentEffort] = Field(default_factory=list)
    splits_metric: list[Split] = Field(default_factory=list)
    splits_standard: list[Split] = Field(default_factory=list)
    laps: list[Lap] = Field(default_factory=list)
    best_efforts: list[DetailedSegmentEffort] = Field(default_factory=list)
    photos: dict[str, object] | None = None


class CreateActivityRequestBody(RequestModel):
    """Body for ``POST /activities``. Requires ``activity:write`` scope.

    Sent as form fields, so the booleans go on the wire as Strava's ``1``/``0`` flags and
    ``start_date_local`` as an ISO 8601 string.
    """

    name: str
    sport_type: str
    start_date_local: datetime
    elapsed_time: Annotated[int, Field(gt=0, description="Duration in seconds.")]
    type: str | None = None
    description: str | None = None
    distance: Annotated[float, Field(ge=0)] | None = None
    trainer: bool | None = None
    commute: bool | None = None

    @field_serializer("start_date_local")
    def _serialize_start_date_local(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("trainer", "commute")
    def _serialize_flags(self, value: bool | None) -> int | None:
        return None if value is None else int(value)


class UpdateActivityRequestBody(RequestModel):
    """Body for ``PUT /activities/{id}``. Requires ``activity:write`` scope.

    Unlike the other writes in this API, this one is a JSON body — the swagger declares
    it ``in: body`` rather than as form fields.
    """

    name: str | None = None
    sport_type: str | None = None
    type: str | None = None
    description: str | None = None
    gear_id: str | None = None
    trainer: bool | None = None
    commute: bool | None = None
    hide_from_home: bool | None = None
