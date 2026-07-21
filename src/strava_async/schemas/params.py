"""Query-parameter models.

These carry every wire concern for the query string: aliasing, CSV joining, and the two
different date encodings Strava uses. Service methods pass them straight through.
"""

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, field_serializer, field_validator, model_validator

from strava_async.schemas.base import RequestModel
from strava_async.schemas.stream_model import StreamKey

__all__ = [
    "ExploreSegmentsParams",
    "GetActivitiesParams",
    "GetActivityParams",
    "GetCommentsParams",
    "GetSegmentEffortsParams",
    "PaginationParams",
    "StreamParams",
]


class PaginationParams(RequestModel):
    """The shared ``page`` / ``per_page`` pair.

    Strava defaults to page 1 and 30 per page; leaving these unset sends neither.
    """

    page: Annotated[int, Field(ge=1)] | None = None
    per_page: Annotated[int, Field(ge=1, le=200)] | None = None


class GetActivitiesParams(PaginationParams):
    """Query for ``GET /athlete/activities``.

    ``before`` and ``after`` go on the wire as epoch seconds. They must be timezone-aware:
    converting a naive datetime would silently depend on the machine's local zone.
    """

    before: datetime | None = None
    after: datetime | None = None

    @field_validator("before", "after")
    @classmethod
    def _require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError(
                "must be timezone-aware, since it is sent as an absolute epoch timestamp"
            )
        return value

    @model_validator(mode="after")
    def _check_window(self) -> Self:
        if self.before is not None and self.after is not None and self.after > self.before:
            raise ValueError("'after' must not be later than 'before'")
        return self

    @field_serializer("before", "after")
    def _serialize_epoch(self, value: datetime | None) -> int | None:
        return None if value is None else int(value.timestamp())


class GetActivityParams(RequestModel):
    """Query for ``GET /activities/{id}``."""

    include_all_efforts: bool | None = None


class GetCommentsParams(PaginationParams):
    """Query for ``GET /activities/{id}/comments``.

    This endpoint offers cursor pagination alongside the page-based kind. Prefer the
    cursor for deep traversal: page-based pagination can skip or repeat comments when
    new ones arrive mid-traversal.
    """

    page_size: Annotated[int, Field(ge=1, le=200)] | None = None
    after_cursor: str | None = None


class GetSegmentEffortsParams(RequestModel):
    """Query for ``GET /segment_efforts``. Requires ``activity:read`` scope.

    The dates here are *local* wall-clock times sent as ISO 8601, which is why they are
    allowed to be naive — unlike the epoch filters on ``GetActivitiesParams``.
    """

    segment_id: int
    start_date_local: datetime | None = None
    end_date_local: datetime | None = None
    per_page: Annotated[int, Field(ge=1, le=200)] | None = None

    @model_validator(mode="after")
    def _check_window(self) -> Self:
        if (
            self.start_date_local is not None
            and self.end_date_local is not None
            and self.start_date_local > self.end_date_local
        ):
            raise ValueError("'start_date_local' must not be later than 'end_date_local'")
        return self

    @field_serializer("start_date_local", "end_date_local")
    def _serialize_iso(self, value: datetime | None) -> str | None:
        return None if value is None else value.isoformat()


class ExploreSegmentsParams(RequestModel):
    """Query for ``GET /segments/explore``.

    ``bounds`` is exactly four floats — south-west latitude and longitude, then
    north-east latitude and longitude — joined with commas on the wire.
    """

    bounds: Annotated[list[float], Field(min_length=4, max_length=4)]
    activity_type: Literal["running", "riding"] | None = None
    min_cat: Annotated[int, Field(ge=0, le=5)] | None = None
    max_cat: Annotated[int, Field(ge=0, le=5)] | None = None

    @model_validator(mode="after")
    def _check_categories(self) -> Self:
        if self.min_cat is not None and self.max_cat is not None and self.min_cat > self.max_cat:
            raise ValueError("'min_cat' must not exceed 'max_cat'")
        return self

    @field_serializer("bounds")
    def _serialize_bounds(self, value: list[float]) -> str:
        return ",".join(str(coordinate) for coordinate in value)


class StreamParams(RequestModel):
    """Query for every ``/streams`` endpoint.

    ``key_by_type`` is pinned to true because Strava requires it, and it is what makes
    the response an object keyed by stream type rather than a bare array.
    """

    keys: Annotated[list[StreamKey], Field(min_length=1)]
    key_by_type: Literal[True] = True

    @field_serializer("keys")
    def _serialize_keys(self, value: list[str]) -> str:
        return ",".join(value)
