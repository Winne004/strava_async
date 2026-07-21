"""The factory that wires everything together.

This is the only module that imports across every layer. Application code calls
``initialise_strava_client()`` and never constructs the pieces itself.
"""

from collections.abc import Callable

import aiohttp

from strava_async.auth.client import StravaAuthClient
from strava_async.client import StravaClient
from strava_async.protocols import AuthClientProtocol
from strava_async.registry import build_service_registry
from strava_async.settings import StravaSettings

__all__ = ["initialise_strava_client"]


def initialise_strava_client(
    settings: StravaSettings | None = None,
    *,
    session: aiohttp.ClientSession | None = None,
    on_token_refresh: Callable[[str], None] | None = None,
) -> StravaClient:
    """Build a configured client.

    Args:
        settings: Configuration. Read from the environment when omitted.
        session: An externally-owned session. When given, the client will use it and
            will not close it on exit.
        on_token_refresh: Called with the new refresh token whenever Strava rotates it.
            Persist it — the token passed in at startup may stop working.

    Returns:
        A client ready to be used as an async context manager.
    """
    # Credentials come from the environment, so the no-argument call is the normal path.
    resolved_settings = settings or StravaSettings()

    def auth_factory(client_session: aiohttp.ClientSession) -> AuthClientProtocol:
        return StravaAuthClient(
            client_session,
            client_id=resolved_settings.client_id,
            client_secret=resolved_settings.client_secret.get_secret_value(),
            refresh_token=resolved_settings.refresh_token.get_secret_value(),
            token_url=resolved_settings.token_url,
            expiry_margin_seconds=resolved_settings.token_expiry_margin_seconds,
            on_token_refresh=on_token_refresh,
        )

    return StravaClient(
        registry=build_service_registry(resolved_settings),
        auth_factory=auth_factory,
        session=session,
        connector_limit=resolved_settings.connector_limit,
        request_timeout_seconds=resolved_settings.request_timeout_seconds,
        max_retry_attempts=resolved_settings.max_retry_attempts,
        max_retry_wait_seconds=resolved_settings.max_retry_wait_seconds,
    )
