"""The ``/segment_efforts`` surface."""

from strava_async.schemas.params import GetSegmentEffortsParams
from strava_async.schemas.segment_effort_model import DetailedSegmentEffort
from strava_async.services.base import Base

__all__ = ["SegmentEffortsService"]


class SegmentEffortsService(Base):
    """The authenticated athlete's attempts at segments."""

    async def get_efforts_by_segment_id(
        self, params: GetSegmentEffortsParams
    ) -> list[DetailedSegmentEffort]:
        """List the authenticated athlete's efforts on a segment.

        Requires ``activity:read`` scope, and a Strava subscription for the date filters.

        Args:
            params: The segment, an optional local date window, and page size.

        Returns:
            The athlete's efforts on that segment.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/segment_efforts",
            model=list[DetailedSegmentEffort],
            params=params,
        )

    async def get_segment_effort_by_id(self, effort_id: int) -> DetailedSegmentEffort:
        """Get one segment effort. Requires ``activity:read`` scope.

        Args:
            effort_id: The identifier of the effort.

        Returns:
            The effort's detailed representation.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/segment_efforts/{effort_id}",
            model=DetailedSegmentEffort,
        )
