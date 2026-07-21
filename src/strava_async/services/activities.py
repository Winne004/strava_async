"""The ``/activities`` surface."""

from strava_async.schemas.activity_model import (
    Comment,
    CreateActivityRequestBody,
    DetailedActivity,
    Lap,
    SummaryActivity,
    UpdateActivityRequestBody,
)
from strava_async.schemas.athlete_model import SummaryAthlete
from strava_async.schemas.params import (
    GetActivitiesParams,
    GetActivityParams,
    GetCommentsParams,
    PaginationParams,
)
from strava_async.schemas.zone_model import ActivityZone
from strava_async.services.base import Base

__all__ = ["ActivitiesService"]


class ActivitiesService(Base):
    """Activities owned by, or visible to, the authenticated athlete."""

    async def create_activity(self, activity: CreateActivityRequestBody) -> DetailedActivity:
        """Create a manual activity. Requires ``activity:write`` scope.

        Args:
            activity: The activity to create.

        Returns:
            The created activity's detailed representation.
        """
        return await self._post_form(
            endpoint=f"{self.base_url}/activities",
            model=DetailedActivity,
            payload=activity,
        )

    async def get_activity_by_id(
        self, activity_id: int, params: GetActivityParams | None = None
    ) -> DetailedActivity:
        """Get one activity. Requires ``activity:read`` scope.

        Requires ``activity:read_all`` for activities the athlete has set to Only You.

        Args:
            activity_id: The identifier of the activity.
            params: Whether to include all segment efforts.

        Returns:
            The activity's detailed representation.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/activities/{activity_id}",
            model=DetailedActivity,
            params=params,
        )

    async def update_activity_by_id(
        self, activity_id: int, activity: UpdateActivityRequestBody
    ) -> DetailedActivity:
        """Update an activity. Requires ``activity:write`` scope.

        Args:
            activity_id: The identifier of the activity.
            activity: The fields to change. Unset fields are left alone.

        Returns:
            The updated activity's detailed representation.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/activities/{activity_id}",
            model=DetailedActivity,
            method="PUT",
            payload=activity,
        )

    async def get_logged_in_athlete_activities(
        self, params: GetActivitiesParams | None = None
    ) -> list[SummaryActivity]:
        """List the authenticated athlete's activities. Requires ``activity:read`` scope.

        Args:
            params: Pagination and the ``before`` / ``after`` time window.

        Returns:
            The athlete's activities, most recent first.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/athlete/activities",
            model=list[SummaryActivity],
            params=params,
        )

    async def get_comments_by_activity_id(
        self, activity_id: int, params: GetCommentsParams | None = None
    ) -> list[Comment]:
        """List an activity's comments. Requires ``activity:read`` scope.

        Args:
            activity_id: The identifier of the activity.
            params: Page-based or cursor-based pagination.

        Returns:
            The comments on the activity.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/activities/{activity_id}/comments",
            model=list[Comment],
            params=params,
        )

    async def get_kudoers_by_activity_id(
        self, activity_id: int, params: PaginationParams | None = None
    ) -> list[SummaryAthlete]:
        """List the athletes who kudoed an activity. Requires ``activity:read`` scope.

        Args:
            activity_id: The identifier of the activity.
            params: Pagination.

        Returns:
            The kudoers, carrying first and last name only.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/activities/{activity_id}/kudos",
            model=list[SummaryAthlete],
            params=params,
        )

    async def get_laps_by_activity_id(self, activity_id: int) -> list[Lap]:
        """List an activity's laps. Requires ``activity:read`` scope.

        Args:
            activity_id: The identifier of the activity.

        Returns:
            The activity's laps, in order.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/activities/{activity_id}/laps",
            model=list[Lap],
        )

    async def get_zones_by_activity_id(self, activity_id: int) -> list[ActivityZone]:
        """Get an activity's time-in-zone distributions.

        Requires ``activity:read`` scope and a Strava subscription.

        Args:
            activity_id: The identifier of the activity.

        Returns:
            One entry per zone type recorded for the activity.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/activities/{activity_id}/zones",
            model=list[ActivityZone],
        )
