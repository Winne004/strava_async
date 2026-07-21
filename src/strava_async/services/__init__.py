"""One module per API surface, each a thin declarative layer over ``Base``."""

from strava_async.services.activities import ActivitiesService
from strava_async.services.athletes import AthletesService
from strava_async.services.base import Base
from strava_async.services.clubs import ClubsService
from strava_async.services.gear import GearService
from strava_async.services.routes import RoutesService
from strava_async.services.segment_efforts import SegmentEffortsService
from strava_async.services.segments import SegmentsService
from strava_async.services.streams import StreamsService
from strava_async.services.uploads import UploadsService

__all__ = [
    "ActivitiesService",
    "AthletesService",
    "Base",
    "ClubsService",
    "GearService",
    "RoutesService",
    "SegmentEffortsService",
    "SegmentsService",
    "StreamsService",
    "UploadsService",
]
