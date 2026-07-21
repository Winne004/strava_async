"""The request pipeline: auth, rate limiting, retries, error mapping, validation."""

from collections.abc import Callable
from typing import Any

import aiohttp
import pytest

from strava_async.exceptions import (
    StravaAuthenticationError,
    StravaConnectionError,
    StravaError,
    StravaNotFoundError,
    StravaPermissionError,
    StravaRateLimitError,
    StravaServerError,
)
from strava_async.schemas.athlete_model import SummaryAthlete
from strava_async.schemas.params import GetActivitiesParams, StreamParams
from strava_async.services.base import Base
from tests.conftest import (
    BASE_URL,
    FakeAuthClient,
    FakeLimiter,
    FakeResponse,
    FakeSession,
    SleepRecorder,
)

ATHLETE_BODY = {"id": 7, "firstname": "Marianne", "lastname": "T"}


async def test_validates_json_into_the_model(make_base: Callable[..., Base]) -> None:
    session = FakeSession(FakeResponse(json_body=ATHLETE_BODY))
    base = make_base(session)

    result = await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert isinstance(result, SummaryAthlete)
    assert result.firstname == "Marianne"


async def test_validates_array_responses_into_a_list(make_base: Callable[..., Base]) -> None:
    """`model=list[X]` goes through the same TypeAdapter path as a bare model."""
    session = FakeSession(FakeResponse(json_body=[ATHLETE_BODY, ATHLETE_BODY]))
    base = make_base(session)

    result = await base.fetch_data(endpoint=f"{BASE_URL}/kudos", model=list[SummaryAthlete])

    assert len(result) == 2
    assert all(isinstance(item, SummaryAthlete) for item in result)


async def test_attaches_auth_headers(
    make_base: Callable[..., Base], auth_client: FakeAuthClient
) -> None:
    session = FakeSession(FakeResponse(json_body=ATHLETE_BODY))
    base = make_base(session)

    await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert auth_client.header_calls == 1
    assert session.last_request["headers"]["Authorization"] == "Bearer test-token"


async def test_acquires_a_rate_limit_slot_per_request(
    make_base: Callable[..., Base], limiter: FakeLimiter
) -> None:
    session = FakeSession(FakeResponse(json_body=ATHLETE_BODY))
    base = make_base(session)

    await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert limiter.acquisitions == 1


async def test_serializes_params_through_the_model(make_base: Callable[..., Base]) -> None:
    """Epoch conversion and CSV joining happen in the schema, not the pipeline."""
    session = FakeSession(FakeResponse(json_body=[]))
    base = make_base(session)

    await base.fetch_data(
        endpoint=f"{BASE_URL}/activities",
        model=list[SummaryAthlete],
        params=StreamParams(keys=["time", "watts"]),
    )

    assert session.last_request["params"] == {"keys": "time,watts", "key_by_type": "true"}


async def test_omits_unset_params(make_base: Callable[..., Base]) -> None:
    session = FakeSession(FakeResponse(json_body=[]))
    base = make_base(session)

    await base.fetch_data(
        endpoint=f"{BASE_URL}/activities",
        model=list[SummaryAthlete],
        params=GetActivitiesParams(per_page=5),
    )

    assert session.last_request["params"] == {"per_page": "5"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [(403, StravaPermissionError), (404, StravaNotFoundError), (500, StravaServerError)],
)
async def test_maps_status_to_exception(
    make_base: Callable[..., Base], status: int, expected: type[StravaError]
) -> None:
    session = FakeSession(FakeResponse(status=status, json_body={"message": "denied"}))
    base = make_base(session)

    with pytest.raises(expected) as caught:
        await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert caught.value.status_code == status
    assert caught.value.endpoint == f"{BASE_URL}/athlete"
    assert caught.value.details == {"message": "denied"}


async def test_surfaces_fault_errors_in_details(make_base: Callable[..., Base]) -> None:
    fault = {
        "message": "Bad Request",
        "errors": [{"resource": "Activity", "field": "name", "code": "required"}],
    }
    session = FakeSession(FakeResponse(status=400, json_body=fault))
    base = make_base(session)

    with pytest.raises(Exception) as caught:
        await base.fetch_data(endpoint=f"{BASE_URL}/activities", model=SummaryAthlete)

    assert caught.value.details["errors"][0]["code"] == "required"  # ty: ignore[unresolved-attribute]


async def test_redacted_endpoint_replaces_the_real_one(make_base: Callable[..., Base]) -> None:
    """A URL embedding a secret must never reach an exception message."""
    session = FakeSession(FakeResponse(status=404, json_body={"message": "gone"}))
    base = make_base(session)

    with pytest.raises(StravaNotFoundError) as caught:
        await base.fetch_data(
            endpoint=f"{BASE_URL}/thing?token=s3cret",
            model=SummaryAthlete,
            error_endpoint=f"{BASE_URL}/thing",
        )

    assert "s3cret" not in str(caught.value)
    assert caught.value.endpoint == f"{BASE_URL}/thing"


async def test_401_invalidates_the_token_and_retries(
    make_base: Callable[..., Base], auth_client: FakeAuthClient
) -> None:
    session = FakeSession(
        FakeResponse(status=401, json_body={"message": "expired"}),
        FakeResponse(json_body=ATHLETE_BODY),
    )
    base = make_base(session)

    result = await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert auth_client.invalidations == 1
    assert auth_client.header_calls == 2
    assert result.id == 7


async def test_401_on_a_non_oauth_request_leaves_the_token_alone(
    make_base: Callable[..., Base], auth_client: FakeAuthClient
) -> None:
    """A 401 from an endpoint we did not authenticate says nothing about our token."""
    session = FakeSession(*[FakeResponse(status=401, json_body={"message": "no"})] * 3)
    base = make_base(session)

    with pytest.raises(StravaAuthenticationError):
        await base.fetch_data(endpoint=f"{BASE_URL}/other", model=SummaryAthlete, uses_oauth=False)

    assert auth_client.invalidations == 0


async def test_retries_transport_failures(make_base: Callable[..., Base]) -> None:
    session = FakeSession(
        aiohttp.ClientConnectionError("reset"), FakeResponse(json_body=ATHLETE_BODY)
    )
    base = make_base(session)

    result = await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert result.id == 7
    assert len(session.requests) == 2


async def test_gives_up_after_the_configured_attempts(
    make_base: Callable[..., Base], sleeper: SleepRecorder
) -> None:
    session = FakeSession(*[aiohttp.ClientConnectionError("reset")] * 3)
    base = make_base(session, max_retry_attempts=3)

    with pytest.raises(StravaConnectionError):
        await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert len(session.requests) == 3
    assert len(sleeper.delays) == 2


async def test_does_not_retry_a_permission_error(make_base: Callable[..., Base]) -> None:
    """403 means a missing scope; retrying cannot conjure one."""
    session = FakeSession(FakeResponse(status=403, json_body={"message": "no scope"}))
    base = make_base(session)

    with pytest.raises(StravaPermissionError):
        await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert len(session.requests) == 1


async def test_429_honours_retry_after(
    make_base: Callable[..., Base], sleeper: SleepRecorder
) -> None:
    session = FakeSession(
        FakeResponse(status=429, json_body={"message": "slow"}, headers={"Retry-After": "12"}),
        FakeResponse(json_body=ATHLETE_BODY),
    )
    base = make_base(session)

    await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert sleeper.delays == [12.0]


async def test_429_without_retry_after_waits_for_the_window(
    make_base: Callable[..., Base], sleeper: SleepRecorder
) -> None:
    """Strava usually omits the header, so fall back to the quarter-hour boundary.

    The clock is pinned to 10:03:00, so the window resets in 12 minutes — but the wait is
    capped so a 429 never becomes a quarter-hour hang.
    """
    session = FakeSession(
        FakeResponse(status=429, json_body={"message": "slow"}),
        FakeResponse(json_body=ATHLETE_BODY),
    )
    base = make_base(session, max_retry_wait_seconds=30.0)

    await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert sleeper.delays == [30.0]


async def test_429_exposes_rate_limit_usage(make_base: Callable[..., Base]) -> None:
    headers = {"X-RateLimit-Limit": "100,1000", "X-RateLimit-Usage": "100,347"}
    session = FakeSession(*[FakeResponse(status=429, json_body={}, headers=headers)] * 3)
    base = make_base(session)

    with pytest.raises(StravaRateLimitError) as caught:
        await base.fetch_data(endpoint=f"{BASE_URL}/athlete", model=SummaryAthlete)

    assert caught.value.details["X-RateLimit-Usage"] == "100,347"
    assert caught.value.retry_after is not None


async def test_get_text_returns_the_raw_document(make_base: Callable[..., Base]) -> None:
    session = FakeSession(FakeResponse(text_body="<gpx></gpx>"))
    base = make_base(session)

    assert await base._get_text(endpoint=f"{BASE_URL}/export") == "<gpx></gpx>"


async def test_get_bytes_returns_raw_bytes(make_base: Callable[..., Base]) -> None:
    session = FakeSession(FakeResponse(bytes_body=b"\x89PNG"))
    base = make_base(session)

    assert await base._get_bytes(endpoint=f"{BASE_URL}/image") == b"\x89PNG"


async def test_a_failing_text_endpoint_still_yields_a_parsed_fault(
    make_base: Callable[..., Base],
) -> None:
    session = FakeSession(FakeResponse(status=404, json_body={"message": "no route"}))
    base = make_base(session)

    with pytest.raises(StravaNotFoundError) as caught:
        await base._get_text(endpoint=f"{BASE_URL}/export")

    assert caught.value.details == {"message": "no route"}


async def test_form_helpers_send_form_bodies_not_json(make_base: Callable[..., Base]) -> None:
    session = FakeSession(FakeResponse(json_body=ATHLETE_BODY))
    base = make_base(session)

    await base._put_form(
        endpoint=f"{BASE_URL}/athlete",
        model=SummaryAthlete,
        payload=GetActivitiesParams(per_page=3),
    )

    request: dict[str, Any] = session.last_request
    assert request["method"] == "PUT"
    assert request["data"] == {"per_page": 3}
    assert request["json"] is None


async def test_fetch_data_sends_json_bodies(make_base: Callable[..., Base]) -> None:
    session = FakeSession(FakeResponse(json_body=ATHLETE_BODY))
    base = make_base(session)

    await base.fetch_data(
        endpoint=f"{BASE_URL}/activities/1",
        model=SummaryAthlete,
        method="PUT",
        payload=GetActivitiesParams(per_page=3),
    )

    assert session.last_request["json"] == {"per_page": 3}
    assert session.last_request["data"] is None
