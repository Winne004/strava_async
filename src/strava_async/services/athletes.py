"""The ``/athlete`` and ``/athletes`` surface."""

from strava_async.schemas.athlete_model import (
    ActivityStats,
    DetailedAthlete,
    UpdateAthleteRequestBody,
    Zones,
)
from strava_async.services.base import Base

__all__ = ["AthletesService"]


class AthletesService(Base):
    """The authenticated athlete's profile, zones, and totals."""

    async def get_logged_in_athlete(self) -> DetailedAthlete:
        """Get the authenticated athlete.

        Tokens with ``profile:read_all`` receive a detailed representation; all others
        receive a summary one, so the detail-only fields come back null.

        Returns:
            The authenticated athlete's profile.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/athlete",
            model=DetailedAthlete,
        )

    async def update_logged_in_athlete(self, athlete: UpdateAthleteRequestBody) -> DetailedAthlete:
        """Update the authenticated athlete. Requires ``profile:write`` scope.

        Note: the swagger declares ``weight`` as a path parameter, which is a defect in
        the spec — Strava takes it as a form field, which is what this sends.

        Args:
            athlete: The fields to change.

        Returns:
            The updated profile.
        """
        return await self._put_form(
            endpoint=f"{self.base_url}/athlete",
            model=DetailedAthlete,
            payload=athlete,
        )

    async def get_logged_in_athlete_zones(self) -> Zones:
        """Get the authenticated athlete's heart-rate and power zones.

        Requires ``profile:read_all`` scope.

        Returns:
            The athlete's configured zones.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/athlete/zones",
            model=Zones,
        )

    async def get_stats(self, athlete_id: int) -> ActivityStats:
        """Get an athlete's activity totals.

        Only covers activities set to Everyone visibility, and the identifier must be
        the authenticated athlete's own.

        Args:
            athlete_id: The identifier of the athlete.

        Returns:
            Recent, year-to-date, and all-time totals per sport.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/athletes/{athlete_id}/stats",
            model=ActivityStats,
        )
