"""End-to-end coverage: a real service through the real pipeline, one test per service.

The other service tests patch a ``Base`` helper and assert the call, which says nothing
about whether the two halves fit together. These drive the genuine
service → ``Base`` → session path with the payloads Strava publishes, so they catch what
mocks structurally cannot: a wrong URL, a parameter that never reaches the query string,
a response the model cannot parse.

Only the socket is fake.
"""

import json
from pathlib import Path
from typing import Any

from strava_async.schemas.activity_model import DetailedActivity
from strava_async.schemas.athlete_model import DetailedAthlete
from strava_async.schemas.club_model import DetailedClub
from strava_async.schemas.gear_model import DetailedGear
from strava_async.schemas.params import (
    ExploreSegmentsParams,
    GetActivityParams,
    GetSegmentEffortsParams,
    StreamParams,
)
from strava_async.schemas.segment_model import ExplorerResponse
from strava_async.schemas.stream_model import StreamSet
from strava_async.schemas.upload_model import Upload
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
from tests.conftest import BASE_URL, FakeAuthClient, FakeLimiter, FakeResponse, FakeSession

FIXTURES = Path(__file__).parent / "fixtures"

# Streams examples predate key_by_type; keying by each entry's own type is the
# transformation the live API performs. See tests/test_fixtures.py.
STREAM_FIXTURES = {"getActivityStreams"}


def fixture(name: str) -> Any:
    payload = json.loads((FIXTURES / f"{name}.json").read_text())
    if name in STREAM_FIXTURES:
        return {stream["type"]: stream for stream in payload}
    return payload


def build[ServiceT: Base](
    service_class: type[ServiceT], *responses: Any
) -> tuple[ServiceT, FakeSession]:
    """A real service on a real Base, wired to a scripted session."""
    session = FakeSession(*responses)
    service = service_class(session, BASE_URL, FakeAuthClient(), FakeLimiter())  # ty: ignore[invalid-argument-type]
    return service, session


async def test_activities_end_to_end() -> None:
    service, session = build(ActivitiesService, FakeResponse(json_body=fixture("getActivityById")))

    activity = await service.get_activity_by_id(
        12345678987654321, GetActivityParams(include_all_efforts=True)
    )

    assert session.last_request["method"] == "GET"
    assert session.last_request["url"] == f"{BASE_URL}/activities/12345678987654321"
    assert session.last_request["params"] == {"include_all_efforts": "true"}
    assert session.last_request["headers"]["Authorization"] == "Bearer test-token"

    assert isinstance(activity, DetailedActivity)
    assert activity.name == "Happy Friday"
    assert activity.sport_type == "MountainBikeRide"


async def test_athletes_end_to_end() -> None:
    service, session = build(AthletesService, FakeResponse(json_body=fixture("getLoggedInAthlete")))

    athlete = await service.get_logged_in_athlete()

    assert session.last_request["url"] == f"{BASE_URL}/athlete"
    assert session.last_request["params"] is None

    assert isinstance(athlete, DetailedAthlete)
    assert athlete.username == "marianne_t"
    assert athlete.bikes[0].name == "EMC"


async def test_clubs_end_to_end() -> None:
    service, session = build(ClubsService, FakeResponse(json_body=fixture("getClubById")))

    club = await service.get_club_by_id(1)

    assert session.last_request["url"] == f"{BASE_URL}/clubs/1"

    assert isinstance(club, DetailedClub)
    assert club.name == "Team Strava Cycling"
    assert club.activity_types == ["Ride", "VirtualRide", "EBikeRide", "Velomobile", "Handcycle"]


async def test_gear_end_to_end() -> None:
    """Gear ids are prefixed strings — a client that assumed ints would build a bad URL."""
    service, session = build(GearService, FakeResponse(json_body=fixture("getGearById")))

    gear = await service.get_gear_by_id("b1231")

    assert session.last_request["url"] == f"{BASE_URL}/gear/b1231"

    assert isinstance(gear, DetailedGear)
    assert gear.brand_name == "BMC"


async def test_routes_end_to_end() -> None:
    """The GPX export is XML, so it must come back as text rather than through the JSON path."""
    service, session = build(RoutesService, FakeResponse(text_body="<gpx><trk/></gpx>"))

    document = await service.get_route_as_gpx(42)

    assert session.last_request["url"] == f"{BASE_URL}/routes/42/export_gpx"
    assert document == "<gpx><trk/></gpx>"


async def test_segments_end_to_end() -> None:
    """Proves the four-float bounds actually reach the wire as one CSV parameter."""
    service, session = build(SegmentsService, FakeResponse(json_body=fixture("exploreSegments")))

    found = await service.explore_segments(
        ExploreSegmentsParams(
            bounds=[37.8331119, -122.4834356, 37.8280722, -122.4981393],
            activity_type="riding",
            min_cat=0,
            max_cat=5,
        )
    )

    assert session.last_request["url"] == f"{BASE_URL}/segments/explore"
    assert session.last_request["params"] == {
        "bounds": "37.8331119,-122.4834356,37.8280722,-122.4981393",
        "activity_type": "riding",
        "min_cat": "0",
        "max_cat": "5",
    }

    assert isinstance(found, ExplorerResponse)
    assert found.segments[0].name == "Hawk Hill"


async def test_segment_efforts_end_to_end() -> None:
    """A list endpoint: the response is a bare array, validated through list[Model]."""
    service, session = build(
        SegmentEffortsService, FakeResponse(json_body=fixture("getEffortsBySegmentId"))
    )

    efforts = await service.get_efforts_by_segment_id(
        GetSegmentEffortsParams(segment_id=788127, per_page=20)
    )

    assert session.last_request["url"] == f"{BASE_URL}/segment_efforts"
    assert session.last_request["params"] == {"segment_id": "788127", "per_page": "20"}

    assert len(efforts) == 1
    assert efforts[0].name == "Alpe d'Huez"
    assert efforts[0].segment is not None
    assert efforts[0].segment.country == "France"


async def test_streams_end_to_end() -> None:
    """Proves keys become CSV and key_by_type is always sent."""
    service, session = build(StreamsService, FakeResponse(json_body=fixture("getActivityStreams")))

    streams = await service.get_activity_streams(12345, StreamParams(keys=["distance", "time"]))

    assert session.last_request["url"] == f"{BASE_URL}/activities/12345/streams"
    assert session.last_request["params"] == {
        "keys": "distance,time",
        "key_by_type": "true",
    }

    assert isinstance(streams, StreamSet)
    assert streams.distance is not None
    assert streams.distance.data[:3] == [2.9, 5.8, 8.5]


async def test_uploads_end_to_end() -> None:
    """The spec has no upload example, so this payload is hand-written from the docs.

    It exercises the plumbing, not the field names — see the coverage note in
    tests/test_fixtures.py.
    """
    service, session = build(
        UploadsService,
        FakeResponse(
            json_body={
                "id": 98765,
                "id_str": "98765",
                "external_id": "ride.gpx",
                "error": None,
                "status": "Your activity is still being processed.",
                "activity_id": None,
            }
        ),
    )

    upload = await service.get_upload_by_id(98765)

    assert session.last_request["url"] == f"{BASE_URL}/uploads/98765"

    assert isinstance(upload, Upload)
    assert upload.is_complete is False


async def test_the_pipeline_is_shared_not_reimplemented() -> None:
    """Every service inherits the same Base, so auth and limiting cannot drift apart."""
    limiter = FakeLimiter()
    auth = FakeAuthClient()
    session = FakeSession(
        FakeResponse(json_body=fixture("getLoggedInAthlete")),
        FakeResponse(json_body=fixture("getGearById")),
    )

    athletes = AthletesService(session, BASE_URL, auth, limiter)  # ty: ignore[invalid-argument-type]
    gear = GearService(session, BASE_URL, auth, limiter)  # ty: ignore[invalid-argument-type]

    await athletes.get_logged_in_athlete()
    await gear.get_gear_by_id("b1231")

    assert limiter.acquisitions == 2
    assert auth.header_calls == 2
