"""The ``/segments`` surface."""

from strava_async.schemas.params import ExploreSegmentsParams, PaginationParams
from strava_async.schemas.segment_model import (
    DetailedSegment,
    ExplorerResponse,
    StarSegmentRequestBody,
    SummarySegment,
)
from strava_async.services.base import Base

__all__ = ["SegmentsService"]


class SegmentsService(Base):
    """Segments, the explorer, and the athlete's starred list."""

    async def get_segment_by_id(self, segment_id: int) -> DetailedSegment:
        """Get one segment. Requires ``read_all`` scope for private segments.

        Args:
            segment_id: The identifier of the segment.

        Returns:
            The segment's detailed representation.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/segments/{segment_id}",
            model=DetailedSegment,
        )

    async def explore_segments(self, params: ExploreSegmentsParams) -> ExplorerResponse:
        """Find the top ten segments in a bounding box. Requires ``read`` scope.

        Args:
            params: The bounding box, and optional activity type and climb-category
                filters.

        Returns:
            The matching segments, in the explorer's own reduced shape.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/segments/explore",
            model=ExplorerResponse,
            params=params,
        )

    async def get_logged_in_athlete_starred_segments(
        self, params: PaginationParams | None = None
    ) -> list[SummarySegment]:
        """List the authenticated athlete's starred segments. Requires ``read`` scope.

        Args:
            params: Pagination.

        Returns:
            The starred segments.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/segments/starred",
            model=list[SummarySegment],
            params=params,
        )

    async def star_segment(self, segment_id: int, body: StarSegmentRequestBody) -> DetailedSegment:
        """Star or unstar a segment. Requires ``profile:write`` scope.

        Args:
            segment_id: The identifier of the segment.
            body: Whether to star or unstar it.

        Returns:
            The segment, with ``starred`` reflecting the change.
        """
        return await self._put_form(
            endpoint=f"{self.base_url}/segments/{segment_id}/starred",
            model=DetailedSegment,
            payload=body,
        )
