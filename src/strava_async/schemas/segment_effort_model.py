"""Segment efforts — one athlete's attempt at one segment."""

from datetime import datetime

from pydantic import Field

from strava_async.schemas.base import ResponseModel
from strava_async.schemas.common import MetaActivity, MetaAthlete
from strava_async.schemas.segment_model import AthleteSegmentStats, SummarySegment

__all__ = ["Achievement", "DetailedSegmentEffort"]


class Achievement(ResponseModel):
    """A placing earned by an effort, such as a personal record or a KOM."""

    type_id: int | None = None
    type: str | None = None
    rank: int | None = None


class DetailedSegmentEffort(ResponseModel):
    """An effort on a segment.

    ``kom_rank`` and ``pr_rank`` are null unless the effort placed in the top ten or set
    a personal record.
    """

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
    average_cadence: float | None = None
    average_watts: float | None = None
    device_watts: bool | None = None
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    segment: SummarySegment | None = None
    kom_rank: int | None = None
    pr_rank: int | None = None
    achievements: list[Achievement] = Field(default_factory=list)
    athlete_segment_stats: AthleteSegmentStats | None = None
    hidden: bool | None = None
