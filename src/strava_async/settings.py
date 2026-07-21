"""Configuration, read from the environment by pydantic-settings.

Field names map to ``STRAVA_``-prefixed environment variables, case-insensitively:
``STRAVA_CLIENT_ID``, ``STRAVA_CLIENT_SECRET``, ``STRAVA_REFRESH_TOKEN``.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["StravaSettings"]

_QUARTER_HOUR_SECONDS = 15 * 60


class StravaSettings(BaseSettings):
    """Credentials, endpoints, and transport tuning for the Strava client."""

    model_config = SettingsConfigDict(
        env_prefix="STRAVA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    client_id: str
    client_secret: SecretStr
    refresh_token: SecretStr

    base_url: str = "https://www.strava.com/api/v3"
    token_url: str = "https://www.strava.com/api/v3/oauth/token"

    # Strava's published defaults. They are set per application and have changed over
    # time, so override via STRAVA_REQUESTS_PER_QUARTER_HOUR / STRAVA_DAILY_REQUEST_LIMIT
    # rather than editing these. See https://developers.strava.com/docs/rate-limits.
    requests_per_quarter_hour: int = Field(default=100, gt=0)
    daily_request_limit: int = Field(default=1000, gt=0)

    max_retry_attempts: int = Field(default=4, ge=1)
    # A rate-limit window can be up to 15 minutes from reset. We surface that figure on
    # the exception but never sleep it inside a retry — the cap keeps a 429 from turning
    # into a quarter-hour hang.
    max_retry_wait_seconds: float = Field(default=60.0, gt=0)

    # Refresh this many seconds before Strava's stated expiry, so a token never expires
    # mid-flight.
    token_expiry_margin_seconds: float = Field(default=300.0, ge=0)

    connector_limit: int = Field(default=10, gt=0)
    request_timeout_seconds: float = Field(default=30.0, gt=0)

    @property
    def requests_per_second(self) -> float:
        """The sustained request rate implied by the 15-minute budget."""
        return self.requests_per_quarter_hour / _QUARTER_HOUR_SECONDS
