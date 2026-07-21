"""Pydantic models for every Strava request and response shape."""

from strava_async.schemas.activity_model import (
    Comment,
    CreateActivityRequestBody,
    DetailedActivity,
    Lap,
    Split,
    SummaryActivity,
    UpdateActivityRequestBody,
)
from strava_async.schemas.athlete_model import (
    ActivityStats,
    ActivityTotal,
    ClubAthlete,
    DetailedAthlete,
    SummaryAthlete,
    UpdateAthleteRequestBody,
    Zones,
)
from strava_async.schemas.base import RequestModel, ResponseModel
from strava_async.schemas.club_model import ClubActivity, DetailedClub, SummaryClub
from strava_async.schemas.common import LatLng, MetaActivity, MetaAthlete, PolylineMap
from strava_async.schemas.fault_model import Error, Fault
from strava_async.schemas.gear_model import DetailedGear, SummaryGear
from strava_async.schemas.params import (
    ExploreSegmentsParams,
    GetActivitiesParams,
    GetSegmentEffortsParams,
    PaginationParams,
    StreamParams,
)
from strava_async.schemas.route_model import Route
from strava_async.schemas.segment_effort_model import DetailedSegmentEffort
from strava_async.schemas.segment_model import (
    DetailedSegment,
    ExplorerResponse,
    ExplorerSegment,
    StarSegmentRequestBody,
    SummarySegment,
)
from strava_async.schemas.stream_model import StreamKey, StreamSet
from strava_async.schemas.upload_model import (
    CreateUploadRequestBody,
    Upload,
    UploadDataType,
)
from strava_async.schemas.zone_model import ActivityZone, TimedZoneRange

__all__ = [
    "ActivityStats",
    "ActivityTotal",
    "ActivityZone",
    "ClubActivity",
    "ClubAthlete",
    "Comment",
    "CreateActivityRequestBody",
    "CreateUploadRequestBody",
    "DetailedActivity",
    "DetailedAthlete",
    "DetailedClub",
    "DetailedGear",
    "DetailedSegment",
    "DetailedSegmentEffort",
    "Error",
    "ExploreSegmentsParams",
    "ExplorerResponse",
    "ExplorerSegment",
    "Fault",
    "GetActivitiesParams",
    "GetSegmentEffortsParams",
    "Lap",
    "LatLng",
    "MetaActivity",
    "MetaAthlete",
    "PaginationParams",
    "PolylineMap",
    "RequestModel",
    "ResponseModel",
    "Route",
    "Split",
    "StarSegmentRequestBody",
    "StreamKey",
    "StreamParams",
    "StreamSet",
    "SummaryActivity",
    "SummaryAthlete",
    "SummaryClub",
    "SummaryGear",
    "SummarySegment",
    "TimedZoneRange",
    "UpdateActivityRequestBody",
    "UpdateAthleteRequestBody",
    "Upload",
    "UploadDataType",
    "Zones",
]
