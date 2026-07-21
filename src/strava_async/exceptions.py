"""Exception hierarchy for the Strava API client.

Every failure raised by this package derives from :class:`StravaError`, so callers can
catch one type and still discriminate by branch (client vs server vs transport) or by a
specific subclass when they care about a particular status.
"""

from typing import Any

__all__ = [
    "StravaAuthenticationError",
    "StravaBadRequestError",
    "StravaClientError",
    "StravaConflictError",
    "StravaConnectionError",
    "StravaError",
    "StravaInternalServerError",
    "StravaNotFoundError",
    "StravaPermissionError",
    "StravaRateLimitError",
    "StravaServerError",
    "StravaServiceUnavailableError",
    "StravaValidationError",
    "map_status_code_to_exception",
]


class StravaError(Exception):
    """Root of the exception hierarchy.

    Args:
        message: Human-readable description of the failure.
        status_code: HTTP status that produced the error, when there was a response.
        endpoint: The endpoint that was called. Callers must pass a redacted URL when
            the real one embeds a secret.
        details: Structured context, typically the parsed Strava ``Fault`` body.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.endpoint = endpoint
        self.details: dict[str, Any] = details or {}

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.endpoint is not None:
            parts.append(f"endpoint={self.endpoint}")
        return " ".join(parts)


class StravaConnectionError(StravaError):
    """The request never produced an HTTP response (DNS, TCP, TLS, or timeout)."""


class StravaClientError(StravaError):
    """The request was rejected by Strava (4xx)."""


class StravaServerError(StravaError):
    """Strava failed to serve the request (5xx)."""


class StravaBadRequestError(StravaClientError):
    """400 — malformed request."""


class StravaAuthenticationError(StravaClientError):
    """401 — missing, expired, or invalid access token.

    Retryable: the pipeline invalidates the cached token and refreshes before retrying.
    """


class StravaPermissionError(StravaClientError):
    """403 — the token is valid but lacks the scope, or the resource is private.

    Not retryable. Refreshing the token cannot add a scope the athlete never granted.
    """


class StravaNotFoundError(StravaClientError):
    """404 — no such resource, or it is not visible to this athlete."""


class StravaConflictError(StravaClientError):
    """409 — the request conflicts with the current state of the resource."""


class StravaValidationError(StravaClientError):
    """422 — Strava rejected the payload; see ``details['errors']``."""


class StravaRateLimitError(StravaClientError):
    """429 — a rate-limit window is exhausted.

    Args:
        retry_after: Seconds to wait before retrying. Taken from a ``Retry-After``
            header when Strava sends one, otherwise the time remaining in the current
            15-minute window.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        status_code: int | None = None,
        endpoint: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, endpoint=endpoint, details=details)
        self.retry_after = retry_after


class StravaInternalServerError(StravaServerError):
    """500 — Strava blew up."""


class StravaServiceUnavailableError(StravaServerError):
    """503 — Strava is down or in maintenance."""


_STATUS_MAP: dict[int, type[StravaError]] = {
    400: StravaBadRequestError,
    401: StravaAuthenticationError,
    403: StravaPermissionError,
    404: StravaNotFoundError,
    409: StravaConflictError,
    422: StravaValidationError,
    429: StravaRateLimitError,
    500: StravaInternalServerError,
    503: StravaServiceUnavailableError,
}


def map_status_code_to_exception(status_code: int) -> type[StravaError]:
    """Return the exception class for an HTTP status.

    Falls back by range so an unmapped 4xx is still distinguishable from an unmapped
    5xx. Add new specific statuses here rather than branching at a call site.

    Args:
        status_code: The HTTP status of the response.

    Returns:
        The most specific exception class registered for that status.
    """
    if status_code in _STATUS_MAP:
        return _STATUS_MAP[status_code]
    if 400 <= status_code < 500:
        return StravaClientError
    if 500 <= status_code < 600:
        return StravaServerError
    return StravaError
