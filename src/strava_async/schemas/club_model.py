"""Clubs, their members, and their activity feed."""

from pydantic import Field

from strava_async.schemas.base import ResponseModel

__all__ = ["ClubActivity", "ClubActivityAthlete", "DetailedClub", "SummaryClub"]


class SummaryClub(ResponseModel):
    """A club as listed."""

    id: int
    resource_state: int | None = None
    name: str | None = None
    profile: str | None = None
    profile_medium: str | None = None
    cover_photo: str | None = None
    cover_photo_small: str | None = None
    sport_type: str | None = None
    activity_types: list[str] = Field(default_factory=list)
    city: str | None = None
    state: str | None = None
    country: str | None = None
    private: bool | None = None
    member_count: int | None = None
    featured: bool | None = None
    verified: bool | None = None
    url: str | None = None


class DetailedClub(SummaryClub):
    """A club fetched on its own, including the caller's standing in it."""

    membership: str | None = None
    admin: bool | None = None
    owner: bool | None = None
    description: str | None = None
    club_type: str | None = None
    post_count: int | None = None
    owner_id: int | None = None
    following_count: int | None = None


class ClubActivityAthlete(ResponseModel):
    """The athlete on a club feed entry — first and last name only, never an id."""

    resource_state: int | None = None
    firstname: str | None = None
    lastname: str | None = None


class ClubActivity(ResponseModel):
    """An entry in a club's activity feed.

    A deliberately thin projection of an activity: the feed carries no identifier, so
    there is nothing to follow through to ``GET /activities/{id}``.
    """

    resource_state: int | None = None
    athlete: ClubActivityAthlete | None = None
    name: str | None = None
    distance: float | None = None
    moving_time: int | None = None
    elapsed_time: int | None = None
    total_elevation_gain: float | None = None
    type: str | None = None
    sport_type: str | None = None
    workout_type: int | None = None
