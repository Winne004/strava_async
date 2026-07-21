"""The exception hierarchy and status mapping."""

import pytest

from strava_async.exceptions import (
    StravaAuthenticationError,
    StravaBadRequestError,
    StravaClientError,
    StravaConflictError,
    StravaError,
    StravaInternalServerError,
    StravaNotFoundError,
    StravaPermissionError,
    StravaRateLimitError,
    StravaServerError,
    StravaServiceUnavailableError,
    StravaValidationError,
    map_status_code_to_exception,
)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, StravaBadRequestError),
        (401, StravaAuthenticationError),
        (403, StravaPermissionError),
        (404, StravaNotFoundError),
        (409, StravaConflictError),
        (422, StravaValidationError),
        (429, StravaRateLimitError),
        (500, StravaInternalServerError),
        (503, StravaServiceUnavailableError),
    ],
)
def test_maps_specific_statuses(status: int, expected: type[StravaError]) -> None:
    assert map_status_code_to_exception(status) is expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [(402, StravaClientError), (418, StravaClientError), (502, StravaServerError)],
)
def test_falls_back_by_range(status: int, expected: type[StravaError]) -> None:
    """An unmapped 4xx stays distinguishable from an unmapped 5xx."""
    assert map_status_code_to_exception(status) is expected


def test_unknown_status_falls_back_to_root() -> None:
    assert map_status_code_to_exception(302) is StravaError


def test_every_specific_error_is_catchable_by_branch() -> None:
    assert issubclass(StravaNotFoundError, StravaClientError)
    assert issubclass(StravaInternalServerError, StravaServerError)
    assert issubclass(StravaClientError, StravaError)
    assert issubclass(StravaServerError, StravaError)


def test_error_carries_context() -> None:
    error = StravaError(
        "boom", status_code=404, endpoint="/activities/1", details={"message": "nope"}
    )
    assert error.status_code == 404
    assert error.endpoint == "/activities/1"
    assert error.details == {"message": "nope"}
    assert "status=404" in str(error)


def test_rate_limit_error_carries_retry_after() -> None:
    error = StravaRateLimitError("slow down", retry_after=42.0, status_code=429)
    assert error.retry_after == 42.0
    assert isinstance(error, StravaClientError)
