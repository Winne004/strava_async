"""The ``/streams`` endpoints, which hang off four different resources."""

from strava_async.schemas.params import StreamParams
from strava_async.schemas.stream_model import StreamSet
from strava_async.services.base import Base

__all__ = ["StreamsService"]


class StreamsService(Base):
    """Per-sample time series for activities, segments, efforts, and routes."""

    async def get_activity_streams(self, activity_id: int, params: StreamParams) -> StreamSet:
        """Get an activity's streams. Requires ``activity:read`` scope.

        Requires ``activity:read_all`` for activities set to Only You.

        Args:
            activity_id: The identifier of the activity.
            params: Which stream types to return.

        Returns:
            The requested streams, keyed by type.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/activities/{activity_id}/streams",
            model=StreamSet,
            params=params,
        )

    async def get_segment_streams(self, segment_id: int, params: StreamParams) -> StreamSet:
        """Get a segment's streams. Requires ``read_all`` scope for private segments.

        Args:
            segment_id: The identifier of the segment.
            params: Which stream types to return.

        Returns:
            The requested streams, keyed by type.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/segments/{segment_id}/streams",
            model=StreamSet,
            params=params,
        )

    async def get_segment_effort_streams(self, effort_id: int, params: StreamParams) -> StreamSet:
        """Get a segment effort's streams. Requires ``activity:read_all`` scope.

        Args:
            effort_id: The identifier of the segment effort.
            params: Which stream types to return.

        Returns:
            The requested streams, keyed by type.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/segment_efforts/{effort_id}/streams",
            model=StreamSet,
            params=params,
        )

    async def get_route_streams(self, route_id: int) -> StreamSet:
        """Get a route's streams. Requires ``read_all`` scope for private routes.

        Unlike the other three, this endpoint takes no ``keys`` parameter — it always
        returns distance, altitude, and latlng.

        Args:
            route_id: The identifier of the route.

        Returns:
            The route's streams, keyed by type.
        """
        return await self.fetch_data(
            endpoint=f"{self.base_url}/routes/{route_id}/streams",
            model=StreamSet,
        )
