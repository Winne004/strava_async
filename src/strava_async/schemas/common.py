"""Types shared across more than one resource."""

from strava_async.schemas.base import ResponseModel

__all__ = ["LatLng", "MetaActivity", "MetaAthlete", "MetaClub", "PolylineMap"]

# Strava sends coordinates as a two-element [latitude, longitude] array, and sends an
# empty array (not null) when it has none.
type LatLng = list[float]


class MetaAthlete(ResponseModel):
    """An athlete reduced to an identifier."""

    id: int | None = None
    resource_state: int | None = None


class MetaActivity(ResponseModel):
    """An activity reduced to an identifier."""

    id: int | None = None
    resource_state: int | None = None


class MetaClub(ResponseModel):
    """A club reduced to an identifier and name."""

    id: int | None = None
    resource_state: int | None = None
    name: str | None = None


class PolylineMap(ResponseModel):
    """An encoded route line.

    ``polyline`` is present on detailed representations, ``summary_polyline`` on summary
    ones. Both stay encoded strings; decoding is out of scope for this client.
    """

    id: str | None = None
    polyline: str | None = None
    summary_polyline: str | None = None
    resource_state: int | None = None
