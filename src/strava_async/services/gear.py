"""The ``/gear`` surface."""

from strava_async.schemas.gear_model import DetailedGear
from strava_async.services.base import Base

__all__ = ["GearService"]


class GearService(Base):
    """Bikes and shoes belonging to the authenticated athlete."""

    async def get_gear_by_id(self, gear_id: str) -> DetailedGear:
        """Get one piece of equipment. Requires ``profile:read_all`` scope.

        Args:
            gear_id: The identifier of the gear. These are strings, not integers —
                ``b`` prefixes a bike and ``g`` a pair of shoes.

        Returns:
            The gear's detailed representation.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/gear/{gear_id}",
            model=DetailedGear,
        )
