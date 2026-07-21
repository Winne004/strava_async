"""Athletes, their zones, and their aggregate stats."""

from datetime import datetime

from pydantic import Field

from strava_async.schemas.base import RequestModel, ResponseModel
from strava_async.schemas.gear_model import SummaryGear

__all__ = [
    "ActivityStats",
    "ActivityTotal",
    "ClubAthlete",
    "DetailedAthlete",
    "HeartRateZoneRanges",
    "PowerZoneRanges",
    "SummaryAthlete",
    "UpdateAthleteRequestBody",
    "ZoneRange",
    "Zones",
]


class SummaryAthlete(ResponseModel):
    """An athlete as embedded in another resource, or listed.

    Everything is optional: a kudoer comes back as nothing but a first and last name,
    while ``/athlete`` returns the full profile.
    """

    id: int | None = None
    resource_state: int | None = None
    firstname: str | None = None
    lastname: str | None = None
    username: str | None = None
    profile: str | None = None
    profile_medium: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    sex: str | None = None
    premium: bool | None = None
    summit: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClubAthlete(SummaryAthlete):
    """A club member, carrying that member's standing in the club."""

    membership: str | None = None
    admin: bool | None = None
    owner: bool | None = None


class DetailedAthlete(SummaryAthlete):
    """The authenticated athlete's full profile.

    ``ftp`` and ``weight`` require ``profile:read_all`` and are null for most athletes.
    """

    follower_count: int | None = None
    friend_count: int | None = None
    mutual_friend_count: int | None = None
    athlete_type: int | None = None
    badge_type_id: int | None = None
    date_preference: str | None = None
    measurement_preference: str | None = None
    ftp: int | None = None
    weight: float | None = None
    clubs: list["SummaryClubRef"] = Field(default_factory=list)
    bikes: list[SummaryGear] = Field(default_factory=list)
    shoes: list[SummaryGear] = Field(default_factory=list)


class SummaryClubRef(ResponseModel):
    """A club as embedded in an athlete profile.

    Deliberately loose: the embedded form is a projection of ``SummaryClub`` and
    importing that here would make the athlete and club modules mutually dependent.
    """

    id: int | None = None
    resource_state: int | None = None
    name: str | None = None
    url: str | None = None


class ZoneRange(ResponseModel):
    """One configured zone boundary. ``max`` is -1 for the open-ended top zone."""

    min: int | None = None
    max: int | None = None


class HeartRateZoneRanges(ResponseModel):
    """The athlete's configured heart-rate zones."""

    custom_zones: bool | None = None
    zones: list[ZoneRange] = Field(default_factory=list)


class PowerZoneRanges(ResponseModel):
    """The athlete's configured power zones."""

    zones: list[ZoneRange] = Field(default_factory=list)


class Zones(ResponseModel):
    """The athlete's zone configuration.

    Note: the ``examples`` block for this endpoint in ``strava_swagger.json`` shows an
    activity-zone payload instead. This model follows the referenced ``Zones`` schema,
    which is what the endpoint actually returns.
    """

    heart_rate: HeartRateZoneRanges | None = None
    power: PowerZoneRanges | None = None


class ActivityTotal(ResponseModel):
    """A rolled-up set of activity totals."""

    count: int | None = None
    distance: float | None = None
    moving_time: int | None = None
    elapsed_time: int | None = None
    elevation_gain: float | None = None
    achievement_count: int | None = None


class ActivityStats(ResponseModel):
    """An athlete's totals, covering only activities visible to Everyone."""

    biggest_ride_distance: float | None = None
    biggest_climb_elevation_gain: float | None = None
    recent_ride_totals: ActivityTotal | None = None
    recent_run_totals: ActivityTotal | None = None
    recent_swim_totals: ActivityTotal | None = None
    ytd_ride_totals: ActivityTotal | None = None
    ytd_run_totals: ActivityTotal | None = None
    ytd_swim_totals: ActivityTotal | None = None
    all_ride_totals: ActivityTotal | None = None
    all_run_totals: ActivityTotal | None = None
    all_swim_totals: ActivityTotal | None = None


class UpdateAthleteRequestBody(RequestModel):
    """Body for ``PUT /athlete``. Requires ``profile:write`` scope."""

    weight: float = Field(gt=0, description="The athlete's weight in kilograms.")
