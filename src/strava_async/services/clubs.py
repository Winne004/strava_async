"""The ``/clubs`` surface."""

from strava_async.schemas.athlete_model import ClubAthlete, SummaryAthlete
from strava_async.schemas.club_model import ClubActivity, DetailedClub, SummaryClub
from strava_async.schemas.params import PaginationParams
from strava_async.services.base import Base

__all__ = ["ClubsService"]


class ClubsService(Base):
    """Clubs the authenticated athlete can see."""

    async def get_logged_in_athlete_clubs(
        self, params: PaginationParams | None = None
    ) -> list[SummaryClub]:
        """List the clubs the authenticated athlete belongs to. Requires ``read`` scope.

        Args:
            params: Pagination.

        Returns:
            The athlete's clubs.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/athlete/clubs",
            model=list[SummaryClub],
            params=params,
        )

    async def get_club_by_id(self, club_id: int) -> DetailedClub:
        """Get one club. Requires ``read`` scope for private clubs.

        Args:
            club_id: The identifier of the club.

        Returns:
            The club's detailed representation.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/clubs/{club_id}",
            model=DetailedClub,
        )

    async def get_club_activities_by_id(
        self, club_id: int, params: PaginationParams | None = None
    ) -> list[ClubActivity]:
        """List a club's recent activities. Requires ``read`` scope.

        Entries carry no identifier, so they cannot be followed through to the full
        activity.

        Args:
            club_id: The identifier of the club.
            params: Pagination.

        Returns:
            The club's activity feed.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/clubs/{club_id}/activities",
            model=list[ClubActivity],
            params=params,
        )

    async def get_club_admins_by_id(
        self, club_id: int, params: PaginationParams | None = None
    ) -> list[SummaryAthlete]:
        """List a club's administrators. Requires ``read`` scope.

        Args:
            club_id: The identifier of the club.
            params: Pagination.

        Returns:
            The club's administrators.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/clubs/{club_id}/admins",
            model=list[SummaryAthlete],
            params=params,
        )

    async def get_club_members_by_id(
        self, club_id: int, params: PaginationParams | None = None
    ) -> list[ClubAthlete]:
        """List a club's members. Requires ``read`` scope.

        Args:
            club_id: The identifier of the club.
            params: Pagination.

        Returns:
            The club's members, each carrying their standing in the club.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/clubs/{club_id}/members",
            model=list[ClubAthlete],
            params=params,
        )
