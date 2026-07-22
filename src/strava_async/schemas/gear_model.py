"""Bikes and shoes."""

from strava_async.schemas.base import ResponseModel

__all__ = ["DetailedGear", "SummaryGear"]


class SummaryGear(ResponseModel):
    """Gear as embedded in an athlete profile."""

    id: str
    resource_state: int | None = None
    primary: bool | None = None
    name: str | None = None
    distance: float | None = None


class DetailedGear(SummaryGear):
    """Gear fetched on its own."""

    brand_name: str | None = None
    model_name: str | None = None
    frame_type: int | None = None
    description: str | None = None
