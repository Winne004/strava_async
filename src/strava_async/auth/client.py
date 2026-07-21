"""OAuth token acquisition, caching, and invalidation.

Strava uses the authorization-code grant. This client does not run the interactive leg:
it takes a stored refresh token and exchanges it for a short-lived access token.
"""

import asyncio
import time
from collections.abc import Callable

import aiohttp

from strava_async.exceptions import (
    StravaConnectionError,
    map_status_code_to_exception,
)

__all__ = ["StravaAuthClient"]

# The token endpoint takes client_secret in the body, so the real URL must never reach an
# exception message or a log line.
_REDACTED_TOKEN_ENDPOINT = "POST /oauth/token"


class StravaAuthClient:
    """Exchanges a refresh token for an access token and caches it.

    Args:
        session: The session to make the token request on.
        client_id: The application's client ID.
        client_secret: The application's client secret.
        refresh_token: A refresh token previously issued to this athlete.
        token_url: The token endpoint.
        expiry_margin_seconds: Refresh this long before Strava's stated expiry.
        on_token_refresh: Called with the new refresh token whenever Strava rotates it.
            Persist it — the previous one may stop working.
        now: Clock, injectable so tests stay deterministic.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        token_url: str,
        expiry_margin_seconds: float = 300.0,
        on_token_refresh: Callable[[str], None] | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._token_url = token_url
        self._expiry_margin_seconds = expiry_margin_seconds
        self._on_token_refresh = on_token_refresh
        self._now = now

        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def refresh_token(self) -> str:
        """The current refresh token, which may differ from the one passed in."""
        return self._refresh_token

    async def get_headers(self) -> dict[str, str]:
        """Return the Authorization header, refreshing the access token if needed.

        Returns:
            A header mapping carrying the bearer token.
        """
        return {"Authorization": f"Bearer {await self.get_access_token()}"}

    async def get_access_token(self) -> str:
        """Return a valid access token, refreshing it if the cache is cold or stale.

        Concurrent callers are serialised on a lock, and the cache is re-checked inside
        it, so a burst of parallel requests triggers exactly one token exchange.

        Returns:
            A currently valid access token.
        """
        cached = self._access_token
        if cached is not None and self._token_is_fresh():
            return cached

        async with self._lock:
            cached = self._access_token
            if cached is not None and self._token_is_fresh():
                return cached
            return await self._refresh()

    def invalidate_token(self) -> None:
        """Drop the cached token so the next call re-fetches it."""
        self._access_token = None
        self._expires_at = 0.0

    def _token_is_fresh(self) -> bool:
        return (
            self._access_token is not None
            and self._now() < self._expires_at - self._expiry_margin_seconds
        )

    async def _refresh(self) -> str:
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }
        try:
            async with self._session.post(self._token_url, data=payload) as response:
                body = await response.json(content_type=None)
                if response.status >= 400:
                    exception_class = map_status_code_to_exception(response.status)
                    raise exception_class(
                        "Failed to refresh the Strava access token.",
                        status_code=response.status,
                        endpoint=_REDACTED_TOKEN_ENDPOINT,
                        details=_fault_details(body),
                    )
        except aiohttp.ClientError as exc:
            raise StravaConnectionError(
                f"Could not reach the Strava token endpoint: {exc}",
                endpoint=_REDACTED_TOKEN_ENDPOINT,
            ) from exc

        access_token = str(body["access_token"])
        self._access_token = access_token
        self._expires_at = float(body["expires_at"])

        rotated = body.get("refresh_token")
        if rotated and rotated != self._refresh_token:
            self._refresh_token = str(rotated)
            if self._on_token_refresh is not None:
                self._on_token_refresh(self._refresh_token)

        return access_token


def _fault_details(body: object) -> dict[str, object]:
    if isinstance(body, dict):
        return {str(key): value for key, value in body.items()}
    return {"body": body}
