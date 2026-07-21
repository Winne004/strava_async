"""Time-in-zone distributions for a single activity."""

from typing import Literal

from pydantic import Field

from strava_async.schemas.base import ResponseModel

__all__ = ["ActivityZone", "TimedZoneRange"]


class TimedZoneRange(ResponseModel):
    """One bucket of a distribution. ``max`` is -1 for the open-ended top bucket."""

    min: int | None = None
    max: int | None = None
    time: int | None = None


class ActivityZone(ResponseModel):
    """How long the athlete spent in each heart-rate or power zone."""

    score: int | None = None
    distribution_buckets: list[TimedZoneRange] = Field(default_factory=list)
    type: Literal["heartrate", "power"] | None = None
    resource_state: int | None = None
    sensor_based: bool | None = None
    points: int | None = None
    custom_zones: bool | None = None
    max: int | None = None
