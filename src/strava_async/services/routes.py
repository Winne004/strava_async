"""The ``/routes`` surface, including the GPX and TCX exports."""

from strava_async.schemas.params import PaginationParams
from strava_async.schemas.route_model import Route
from strava_async.services.base import Base

__all__ = ["RoutesService"]


class RoutesService(Base):
    """Planned routes, as opposed to activities, which were actually ridden or run."""

    async def get_routes_by_athlete_id(
        self, athlete_id: int, params: PaginationParams | None = None
    ) -> list[Route]:
        """List an athlete's routes. Requires ``read_all`` scope for private routes.

        Args:
            athlete_id: The identifier of the athlete.
            params: Pagination.

        Returns:
            The athlete's routes.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/athletes/{athlete_id}/routes",
            model=list[Route],
            params=params,
        )

    async def get_route_by_id(self, route_id: int) -> Route:
        """Get one route. Requires ``read_all`` scope for private routes.

        Args:
            route_id: The identifier of the route.

        Returns:
            The route.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/routes/{route_id}",
            model=Route,
        )

    async def get_route_as_gpx(self, route_id: int) -> str:
        """Export a route as GPX. Requires ``read_all`` scope for private routes.

        Args:
            route_id: The identifier of the route.

        Returns:
            The GPX document, as XML text.
        """
        return await self._get_text(endpoint=f"{self.base_url}/routes/{route_id}/export_gpx")

    async def get_route_as_tcx(self, route_id: int) -> str:
        """Export a route as TCX. Requires ``read_all`` scope for private routes.

        Args:
            route_id: The identifier of the route.

        Returns:
            The TCX document, as XML text.
        """
        return await self._get_text(endpoint=f"{self.base_url}/routes/{route_id}/export_tcx")
