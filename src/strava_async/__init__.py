"""An async Python client for the Strava API v3.

async with initialise_strava_client() as client:
    athlete = await client.athletes.get_logged_in_athlete()
"""

from strava_async.client import StravaClient
from strava_async.exceptions import (
    StravaAuthenticationError,
    StravaBadRequestError,
    StravaClientError,
    StravaConflictError,
    StravaConnectionError,
    StravaError,
    StravaInternalServerError,
    StravaNotFoundError,
    StravaPermissionError,
    StravaRateLimitError,
    StravaServerError,
    StravaServiceUnavailableError,
    StravaValidationError,
)
from strava_async.initialise import initialise_strava_client
from strava_async.settings import StravaSettings

__all__ = [
    "StravaAuthenticationError",
    "StravaBadRequestError",
    "StravaClient",
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
    "StravaSettings",
    "StravaValidationError",
    "initialise_strava_client",
]
