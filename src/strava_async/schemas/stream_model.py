"""Streams — the per-sample time series behind an activity, segment, or route.

Every stream endpoint requires ``key_by_type=true``, so the response is an object keyed
by stream type rather than the array shown in the swagger's ``examples`` block.
"""

from typing import Literal

from pydantic import Field

from strava_async.schemas.base import ResponseModel
from strava_async.schemas.common import LatLng

__all__ = [
    "AltitudeStream",
    "CadenceStream",
    "DistanceStream",
    "HeartrateStream",
    "LatLngStream",
    "MovingStream",
    "PowerStream",
    "SmoothGradeStream",
    "SmoothVelocityStream",
    "StreamKey",
    "StreamSet",
    "TemperatureStream",
    "TimeStream",
]

type StreamKey = Literal[
    "time",
    "distance",
    "latlng",
    "altitude",
    "velocity_smooth",
    "heartrate",
    "cadence",
    "watts",
    "temp",
    "moving",
    "grade_smooth",
]


class BaseStream(ResponseModel):
    """Fields every stream carries."""

    original_size: int | None = None
    resolution: Literal["low", "medium", "high"] | None = None
    series_type: Literal["distance", "time"] | None = None


class TimeStream(BaseStream):
    """Seconds elapsed from the start."""

    data: list[int] = Field(default_factory=list)


class DistanceStream(BaseStream):
    """Metres travelled from the start."""

    data: list[float] = Field(default_factory=list)


class LatLngStream(BaseStream):
    """Positions as ``[latitude, longitude]`` pairs."""

    data: list[LatLng] = Field(default_factory=list)


class AltitudeStream(BaseStream):
    """Altitude in metres."""

    data: list[float] = Field(default_factory=list)


class SmoothVelocityStream(BaseStream):
    """Speed in metres per second."""

    data: list[float] = Field(default_factory=list)


class HeartrateStream(BaseStream):
    """Heart rate in beats per minute."""

    data: list[int] = Field(default_factory=list)


class CadenceStream(BaseStream):
    """Cadence in revolutions per minute."""

    data: list[int] = Field(default_factory=list)


class PowerStream(BaseStream):
    """Power output in watts."""

    data: list[int] = Field(default_factory=list)


class TemperatureStream(BaseStream):
    """Temperature in degrees Celsius."""

    data: list[int] = Field(default_factory=list)


class MovingStream(BaseStream):
    """Whether the athlete was moving at each sample."""

    data: list[bool] = Field(default_factory=list)


class SmoothGradeStream(BaseStream):
    """Grade as a percentage."""

    data: list[float] = Field(default_factory=list)


class StreamSet(ResponseModel):
    """The requested streams, keyed by type.

    Only the keys asked for are populated; the rest stay ``None``.
    """

    time: TimeStream | None = None
    distance: DistanceStream | None = None
    latlng: LatLngStream | None = None
    altitude: AltitudeStream | None = None
    velocity_smooth: SmoothVelocityStream | None = None
    heartrate: HeartrateStream | None = None
    cadence: CadenceStream | None = None
    watts: PowerStream | None = None
    temp: TemperatureStream | None = None
    moving: MovingStream | None = None
    grade_smooth: SmoothGradeStream | None = None
