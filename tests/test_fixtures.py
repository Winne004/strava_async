"""Response models checked against payloads Strava publishes.

Every file in ``tests/fixtures/`` is lifted verbatim from an ``examples`` block in
``context/strava_swagger.json`` — they are Strava's own sample responses, not payloads
invented here. ``test_fixture_matches_the_published_example`` pins that provenance, so a
fixture cannot be quietly edited to make a model pass.

Validating an all-optional model against a payload proves very little on its own: it would
succeed against ``{}``. So each case also probes concrete values, which is what actually
catches a misspelled or missing field.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import TypeAdapter

from strava_async.schemas.activity_model import (
    Comment,
    DetailedActivity,
    Lap,
    SummaryActivity,
)
from strava_async.schemas.athlete_model import ClubAthlete, DetailedAthlete, SummaryAthlete
from strava_async.schemas.club_model import ClubActivity, DetailedClub, SummaryClub
from strava_async.schemas.gear_model import DetailedGear
from strava_async.schemas.segment_effort_model import DetailedSegmentEffort
from strava_async.schemas.segment_model import (
    DetailedSegment,
    ExplorerResponse,
    SummarySegment,
)
from strava_async.schemas.stream_model import StreamSet
from strava_async.schemas.zone_model import ActivityZone

FIXTURES = Path(__file__).parent / "fixtures"
SPEC = Path(__file__).resolve().parent.parent / "context" / "strava_swagger.json"

# Endpoints whose streams example predates `key_by_type`: the payload is an array of
# streams, while the API (which requires key_by_type=true) returns them keyed by type.
# Keying the array by each entry's own `type` is exactly that transformation.
STREAM_FIXTURES = {
    "getActivityStreams",
    "getSegmentStreams",
    "getSegmentEffortStreams",
    "getRouteStreams",
}

# fixture name -> (model, {dotted path: expected value})
CASES: dict[str, tuple[Any, dict[str, Any]]] = {
    "getLoggedInAthlete": (
        DetailedAthlete,
        {
            "id": 1234567890987654321,
            "username": "marianne_t",
            "measurement_preference": "feet",
            "ftp": None,
            "bikes.0.id": "b12345678987655",
            "shoes.0.distance": 4904.0,
        },
    ),
    "updateLoggedInAthlete": (DetailedAthlete, {"firstname": "Marianne", "lastname": "V."}),
    "getLoggedInAthleteZones": (
        # The spec files an activity-zone payload under the athlete-zones endpoint; the
        # shape is genuine, the placement is a defect. See Zones in athlete_model.
        list[ActivityZone],
        {"0.type": "power", "0.sensor_based": True, "0.distribution_buckets.1.time": 62},
    ),
    "getActivityById": (
        DetailedActivity,
        {
            "id": 12345678987654321,
            "name": "Happy Friday",
            "distance": 28099.0,
            "sport_type": "MountainBikeRide",
            "external_id": "garmin_push_12345678987654321",
            "map.id": "a1410355832",
        },
    ),
    "createActivity": (
        DetailedActivity,
        {"id": 123456778928065, "manual": True, "gear_id": "b453542543", "calories": 0.0},
    ),
    "updateActivityById": (
        DetailedActivity,
        {"id": 12345678987654321, "location_country": "United States"},
    ),
    "getLoggedInAthleteActivities": (
        list[SummaryActivity],
        {
            "0.id": 154504250376823,
            "0.device_name": "Garmin Edge 1030",
            "0.average_watts": 175.3,
            "0.suffer_score": 82,
            "0.start_latlng": None,
        },
    ),
    "getLapsByActivityId": (
        list[Lap],
        {"0.lap_index": 1, "0.split": 1, "0.max_speed": 9.4, "0.average_cadence": 79.0},
    ),
    "getCommentsByActivityId": (
        list[Comment],
        {
            "0.text": "Good job and keep the cat pictures coming!",
            "0.athlete.firstname": "Peter",
            "0.cursor": "abc123%20",
        },
    ),
    "getKudoersByActivityId": (
        list[SummaryAthlete],
        {"0.firstname": "Peter", "0.lastname": "S", "0.id": None},
    ),
    "getClubById": (
        DetailedClub,
        {
            "id": 1,
            "sport_type": "cycling",
            "membership": "member",
            "owner_id": 759,
            "activity_types.0": "Ride",
        },
    ),
    "getLoggedInAthleteClubs": (
        list[SummaryClub],
        {"0.id": 231407, "0.member_count": 93151, "0.verified": True},
    ),
    "getClubMembersById": (
        list[ClubAthlete],
        {"0.firstname": "Peter", "0.membership": "member", "0.admin": False},
    ),
    "getClubAdminsById": (list[SummaryAthlete], {"0.firstname": "Peter", "0.lastname": "S."}),
    "getClubActivitiesById": (
        list[ClubActivity],
        {"0.name": "World Championship", "0.athlete.firstname": "Peter", "0.distance": 2641.7},
    ),
    "getGearById": (
        DetailedGear,
        {"id": "b1231", "brand_name": "BMC", "frame_type": 3, "distance": 388206.0},
    ),
    "getSegmentById": (
        DetailedSegment,
        {
            "id": 229781,
            "name": "Hawk Hill",
            "climb_category": 1,
            "start_latlng": [37.8331119, -122.4834356],
            "athlete_segment_stats.effort_count": 2,
            "effort_count": 309974,
        },
    ),
    "starSegment": (DetailedSegment, {"id": 229781, "starred": False}),
    "getLoggedInAthleteStarredSegments": (
        # The spec's example here is a single object although the schema is an array.
        SummarySegment,
        {"id": 229781, "activity_type": "Ride", "private": False},
    ),
    "exploreSegments": (
        ExplorerResponse,
        {
            "segments.0.id": 229781,
            "segments.0.climb_category_desc": "4",
            "segments.0.avg_grade": 5.7,
            "segments.0.elev_difference": 152.8,
        },
    ),
    "getSegmentEffortById": (
        DetailedSegmentEffort,
        {
            "id": 1234556789,
            "name": "Alpe d'Huez",
            "elapsed_time": 381,
            "segment.id": 63450,
            "kom_rank": None,
            "athlete_segment_stats.pr_elapsed_time": 212,
        },
    ),
    "getEffortsBySegmentId": (
        list[DetailedSegmentEffort],
        {
            "0.id": 123456789,
            "0.average_watts": 220.2,
            "0.device_watts": False,
            "0.segment.country": "France",
        },
    ),
    "getActivityStreams": (
        StreamSet,
        {"distance.original_size": 12, "distance.resolution": "high", "distance.data.0": 2.9},
    ),
    "getSegmentStreams": (
        StreamSet,
        {
            "latlng.data.0": [37.833112, -122.483436],
            "altitude.data.1": 93.4,
            "distance.data.1": 16.8,
        },
    ),
    "getSegmentEffortStreams": (StreamSet, {"distance.original_size": 14}),
    "getRouteStreams": (StreamSet, {"latlng.data.1": [37.832964, -122.483406]}),
}

# Services whose endpoints carry no example in the spec. Their models were written from
# Strava's prose documentation and remain unverified against a real response.
SERVICES_WITHOUT_FIXTURES = {"routes", "uploads"}


def load(name: str) -> Any:
    payload = json.loads((FIXTURES / f"{name}.json").read_text())
    if name in STREAM_FIXTURES:
        return {stream["type"]: stream for stream in payload}
    return payload


def resolve(value: Any, path: str) -> Any:
    for part in path.split("."):
        value = value[int(part)] if part.isdigit() else getattr(value, part)
    return value


@pytest.mark.parametrize("name", sorted(CASES), ids=sorted(CASES))
def test_model_parses_the_published_payload(name: str) -> None:
    model, probes = CASES[name]
    parsed = TypeAdapter(model).validate_python(load(name))

    for path, expected in probes.items():
        assert resolve(parsed, path) == expected, f"{name}: {path}"


@pytest.mark.parametrize("name", sorted(CASES), ids=sorted(CASES))
def test_fixture_matches_the_published_example(name: str) -> None:
    """Provenance: the fixture is the spec's example, byte-for-byte in structure."""
    spec = json.loads(SPEC.read_text())
    examples = [
        response["examples"]["application/json"]
        for operations in spec["paths"].values()
        for operation in operations.values()
        if isinstance(operation, dict) and operation.get("operationId") == name
        for response in operation.get("responses", {}).values()
        if "examples" in response
    ]

    assert examples, f"No example in the spec for {name}"
    assert json.loads((FIXTURES / f"{name}.json").read_text()) == examples[0]


def test_every_fixture_is_exercised() -> None:
    """A fixture nobody validates is dead weight; adding one should force a case."""
    on_disk = {path.stem for path in FIXTURES.glob("*.json")}

    assert on_disk == set(CASES)


def test_coverage_gap_is_declared() -> None:
    """The spec has no example for routes or uploads — keep that visible, not forgotten.

    If Strava ever publishes examples for these, this test fails and the fixtures should
    be added rather than the exemption widened.
    """
    spec = json.loads(SPEC.read_text())
    tagged: dict[str, bool] = {}
    for operations in spec["paths"].values():
        for operation in operations.values():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            for tag in operation.get("tags", []):
                has_example = any(
                    "examples" in response for response in operation.get("responses", {}).values()
                )
                tagged[tag] = tagged.get(tag, False) or has_example

    without = {tag.lower() for tag, has_example in tagged.items() if not has_example}

    assert without == SERVICES_WITHOUT_FIXTURES
