"""Schema behaviour: validation, serialization, and the payload shapes Strava sends.

The response fixtures are lifted from the ``examples`` blocks in
``context/strava_swagger.json``, so they are real Strava payloads rather than invented
ones.
"""

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from strava_async.schemas.activity_model import (
    CreateActivityRequestBody,
    SummaryActivity,
    UpdateActivityRequestBody,
)
from strava_async.schemas.athlete_model import ClubAthlete, DetailedAthlete, SummaryAthlete
from strava_async.schemas.club_model import DetailedClub
from strava_async.schemas.gear_model import DetailedGear
from strava_async.schemas.params import (
    ExploreSegmentsParams,
    GetActivitiesParams,
    GetSegmentEffortsParams,
    PaginationParams,
    StreamParams,
)
from strava_async.schemas.route_model import Route
from strava_async.schemas.segment_model import DetailedSegment, StarSegmentRequestBody
from strava_async.schemas.stream_model import StreamSet
from strava_async.schemas.upload_model import CreateUploadRequestBody, Upload


def dump(model: object) -> dict:
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)  # ty: ignore[unresolved-attribute]


# --- Query parameter serialization -------------------------------------------------


def test_pagination_omits_unset_fields() -> None:
    assert dump(PaginationParams()) == {}
    assert dump(PaginationParams(page=2)) == {"page": 2}


def test_activity_time_filters_become_epoch_seconds() -> None:
    params = GetActivitiesParams(after=datetime(2026, 1, 1, tzinfo=UTC))

    assert dump(params) == {"after": 1767225600}


def test_naive_time_filters_are_rejected() -> None:
    """An epoch conversion on a naive datetime would depend on the local timezone."""
    with pytest.raises(ValidationError, match="timezone-aware"):
        GetActivitiesParams(after=datetime(2026, 1, 1))


def test_inverted_activity_window_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must not be later than"):
        GetActivitiesParams(
            after=datetime(2026, 2, 1, tzinfo=UTC), before=datetime(2026, 1, 1, tzinfo=UTC)
        )


def test_segment_effort_dates_are_iso_and_may_be_naive() -> None:
    """These are local wall-clock times, not instants, so naive is correct here."""
    params = GetSegmentEffortsParams(segment_id=42, start_date_local=datetime(2026, 1, 1, 9))

    assert dump(params) == {"segment_id": 42, "start_date_local": "2026-01-01T09:00:00"}


def test_explore_bounds_serialize_as_csv() -> None:
    params = ExploreSegmentsParams(bounds=[37.8, -122.5, 37.9, -122.4])

    assert dump(params)["bounds"] == "37.8,-122.5,37.9,-122.4"


@pytest.mark.parametrize("bounds", [[1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0, 5.0]])
def test_explore_bounds_must_be_exactly_four(bounds: list[float]) -> None:
    with pytest.raises(ValidationError):
        ExploreSegmentsParams(bounds=bounds)


def test_explore_rejects_inverted_climb_categories() -> None:
    with pytest.raises(ValidationError, match="must not exceed"):
        ExploreSegmentsParams(bounds=[1.0, 2.0, 3.0, 4.0], min_cat=4, max_cat=2)


def test_explore_rejects_out_of_range_category() -> None:
    with pytest.raises(ValidationError):
        ExploreSegmentsParams(bounds=[1.0, 2.0, 3.0, 4.0], min_cat=9)


def test_stream_keys_serialize_as_csv_with_key_by_type_pinned() -> None:
    assert dump(StreamParams(keys=["time", "latlng"])) == {
        "keys": "time,latlng",
        "key_by_type": True,
    }


def test_stream_keys_reject_unknown_types() -> None:
    with pytest.raises(ValidationError):
        StreamParams(keys=["not_a_stream"])  # ty: ignore[invalid-argument-type]


def test_stream_keys_must_not_be_empty() -> None:
    with pytest.raises(ValidationError):
        StreamParams(keys=[])


# --- Request bodies ----------------------------------------------------------------


def test_create_activity_encodes_flags_as_strava_expects() -> None:
    """Strava's form fields want 1/0, and the date as ISO 8601."""
    body = CreateActivityRequestBody(
        name="Chill Day",
        sport_type="MountainBikeRide",
        start_date_local=datetime(2026, 2, 20, 10, 2, 13),
        elapsed_time=18373,
        trainer=True,
        commute=False,
    )

    assert dump(body) == {
        "name": "Chill Day",
        "sport_type": "MountainBikeRide",
        "start_date_local": "2026-02-20T10:02:13",
        "elapsed_time": 18373,
        "trainer": 1,
        "commute": 0,
    }


def test_create_activity_requires_a_positive_duration() -> None:
    with pytest.raises(ValidationError):
        CreateActivityRequestBody(
            name="x", sport_type="Ride", start_date_local=datetime(2026, 1, 1), elapsed_time=0
        )


def test_request_bodies_reject_unknown_fields() -> None:
    """A typo should fail here, not be silently dropped on the wire."""
    with pytest.raises(ValidationError):
        StarSegmentRequestBody(**{"startled": True})


def test_update_activity_sends_only_what_was_set() -> None:
    assert dump(UpdateActivityRequestBody(name="Renamed")) == {"name": "Renamed"}


def test_upload_body_rejects_an_unsupported_format() -> None:
    with pytest.raises(ValidationError):
        CreateUploadRequestBody(data_type="csv")  # ty: ignore[invalid-argument-type]


def test_upload_body_accepts_the_documented_formats() -> None:
    assert dump(CreateUploadRequestBody(data_type="fit.gz")) == {"data_type": "fit.gz"}


# --- Response parsing --------------------------------------------------------------


def test_parses_the_athlete_example() -> None:
    athlete = DetailedAthlete.model_validate(
        {
            "id": 1234567890987654321,
            "username": "marianne_t",
            "resource_state": 3,
            "firstname": "Marianne",
            "lastname": "Teutenberg",
            "measurement_preference": "feet",
            "ftp": None,
            "weight": 0,
            "clubs": [],
            "bikes": [{"id": "b12345", "primary": True, "name": "EMC", "distance": 0}],
            "shoes": [{"id": "g12345", "primary": True, "name": "adidas", "distance": 4904}],
        }
    )

    assert athlete.username == "marianne_t"
    assert athlete.ftp is None
    assert athlete.bikes[0].id == "b12345"


def test_parses_the_activity_example_without_converting_times() -> None:
    activity = SummaryActivity.model_validate(
        {
            "id": 154504250376823,
            "name": "Happy Friday",
            "distance": 24931.4,
            "start_date": "2018-05-02T12:15:09Z",
            "start_date_local": "2018-05-02T05:15:09Z",
            "timezone": "(GMT-08:00) America/Los_Angeles",
            "start_latlng": None,
            "map": {"id": "a123", "summary_polyline": None, "resource_state": 2},
        }
    )

    assert activity.start_date is not None
    assert activity.start_date_local is not None
    assert activity.start_date.hour == 12
    assert activity.start_date_local.hour == 5


def test_latlng_parses_as_a_coordinate_pair() -> None:
    segment = DetailedSegment.model_validate(
        {"id": 229781, "start_latlng": [37.8331119, -122.4834356], "end_latlng": []}
    )

    assert segment.start_latlng == [37.8331119, -122.4834356]
    assert segment.end_latlng == []


def test_polyline_stays_an_encoded_string() -> None:
    segment = DetailedSegment.model_validate(
        {"id": 1, "map": {"id": "s1", "polyline": "}g|eFnpqjV", "resource_state": 3}}
    )

    assert segment.map is not None
    assert segment.map.polyline == "}g|eFnpqjV"


def test_unknown_response_fields_are_tolerated() -> None:
    """Strava adds fields without notice; a strict model would be an outage."""
    gear = DetailedGear.model_validate(
        {"id": "b1231", "brand_name": "BMC", "a_field_invented_next_year": True}
    )

    assert gear.brand_name == "BMC"


def test_parses_a_stream_set_keyed_by_type() -> None:
    streams = StreamSet.model_validate(
        {
            "distance": {"data": [2.9, 5.8], "series_type": "distance", "resolution": "high"},
            "latlng": {"data": [[37.83, -122.48], [37.83, -122.48]]},
        }
    )

    assert streams.distance is not None
    assert streams.distance.data == [2.9, 5.8]
    assert streams.latlng is not None
    assert streams.latlng.data[0] == [37.83, -122.48]
    assert streams.heartrate is None


def test_parses_the_club_example() -> None:
    club = DetailedClub.model_validate(
        {
            "id": 1,
            "name": "Team Strava Cycling",
            "sport_type": "cycling",
            "activity_types": ["Ride", "VirtualRide"],
            "membership": "member",
            "owner_id": 759,
        }
    )

    assert club.activity_types == ["Ride", "VirtualRide"]
    assert club.membership == "member"


@pytest.mark.parametrize(
    ("payload", "complete"),
    [
        ({"id": 1, "status": "Your activity is still being processed."}, False),
        ({"id": 1, "activity_id": 42}, True),
        ({"id": 1, "error": "There was an error processing your activity."}, True),
    ],
)
def test_upload_completion_reflects_strava_s_terminal_states(payload: dict, complete: bool) -> None:
    assert Upload.model_validate(payload).is_complete is complete


# --- Required identifiers ----------------------------------------------------------


@pytest.mark.parametrize(
    "model",
    [Route, Upload, DetailedSegment, DetailedGear, DetailedAthlete, SummaryActivity],
    ids=lambda model: model.__name__,
)
def test_a_payload_without_an_id_is_rejected(model: type[BaseModel]) -> None:
    """These once validated `{}` happily, so a misspelled field read as None forever.

    Requiring the identifier turns that silent failure into a loud one.
    """
    with pytest.raises(ValidationError, match="id"):
        model.model_validate({})


def test_kudoers_still_parse_without_an_id() -> None:
    """SummaryAthlete must stay permissive: a kudoer really is just two names."""
    kudoer = SummaryAthlete.model_validate({"firstname": "Peter", "lastname": "S"})

    assert kudoer.id is None
    assert kudoer.firstname == "Peter"


def test_club_members_still_parse_without_an_id() -> None:
    member = ClubAthlete.model_validate(
        {"resource_state": 2, "firstname": "Peter", "lastname": "S.", "membership": "member"}
    )

    assert member.id is None
    assert member.membership == "member"
