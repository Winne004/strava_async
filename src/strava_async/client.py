"""The async client: session lifecycle and lazy service access.

This module deliberately knows nothing about settings or the concrete auth client. It
receives a registry and an auth factory typed via ``protocols``, which is what keeps it
substitutable in tests.
"""

from types import TracebackType
from typing import Self

import aiohttp

from strava_async.protocols import AuthClientFactory, AuthClientProtocol
from strava_async.registry import ServiceRegistry
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

__all__ = ["StravaClient"]

_OUTSIDE_CONTEXT = (
    "StravaClient must be used as an async context manager: "
    "`async with initialise_strava_client() as client:`"
)


class StravaClient:
    """Entry point to every Strava service.

    Construct it with ``initialise_strava_client()`` rather than by hand, and always use
    it as an async context manager.

    Args:
        registry: Service name to configuration.
        auth_factory: Builds the auth client once a session exists.
        session: An externally-owned session. When given, the client uses it and does
            not close it.
        connector_limit: Maximum simultaneous connections for a client-owned session.
        request_timeout_seconds: Total timeout for a client-owned session.
        max_retry_attempts: Passed to each service's request pipeline.
        max_retry_wait_seconds: Passed to each service's request pipeline.
    """

    def __init__(
        self,
        *,
        registry: ServiceRegistry,
        auth_factory: AuthClientFactory,
        session: aiohttp.ClientSession | None = None,
        connector_limit: int = 10,
        request_timeout_seconds: float = 30.0,
        max_retry_attempts: int = 4,
        max_retry_wait_seconds: float = 60.0,
    ) -> None:
        self._registry = registry
        self._auth_factory = auth_factory
        self._connector_limit = connector_limit
        self._request_timeout_seconds = request_timeout_seconds
        self._max_retry_attempts = max_retry_attempts
        self._max_retry_wait_seconds = max_retry_wait_seconds

        self._session = session
        self._owns_session = session is None
        self._auth_client: AuthClientProtocol | None = None
        self._services: dict[str, Base] = {}

    async def __aenter__(self) -> Self:
        """Open the session, unless one was injected."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=self._connector_limit),
                timeout=aiohttp.ClientTimeout(total=self._request_timeout_seconds),
            )
            self._owns_session = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the session if we own it, and drop everything bound to it."""
        if self._session is not None and self._owns_session:
            await self._session.close()
        self._session = None
        self._services.clear()
        self._auth_client = None

    @property
    def auth(self) -> AuthClientProtocol:
        """The auth client, created on first access and cached for the context."""
        if self._session is None:
            raise RuntimeError(_OUTSIDE_CONTEXT)
        if self._auth_client is None:
            self._auth_client = self._auth_factory(self._session)
        return self._auth_client

    @property
    def activities(self) -> ActivitiesService:
        """Activities, comments, kudos, laps, and zones."""
        return self._get_service("activities", ActivitiesService)

    @property
    def athletes(self) -> AthletesService:
        """The authenticated athlete's profile, zones, and totals."""
        return self._get_service("athletes", AthletesService)

    @property
    def clubs(self) -> ClubsService:
        """Clubs, their members, and their activity feed."""
        return self._get_service("clubs", ClubsService)

    @property
    def gear(self) -> GearService:
        """Bikes and shoes."""
        return self._get_service("gear", GearService)

    @property
    def routes(self) -> RoutesService:
        """Routes and their GPX/TCX exports."""
        return self._get_service("routes", RoutesService)

    @property
    def segment_efforts(self) -> SegmentEffortsService:
        """The athlete's attempts at segments."""
        return self._get_service("segment_efforts", SegmentEffortsService)

    @property
    def segments(self) -> SegmentsService:
        """Segments, the explorer, and starred segments."""
        return self._get_service("segments", SegmentsService)

    @property
    def streams(self) -> StreamsService:
        """Per-sample time series for four different resources."""
        return self._get_service("streams", StreamsService)

    @property
    def uploads(self) -> UploadsService:
        """Activity file uploads."""
        return self._get_service("uploads", UploadsService)

    def _get_service[ServiceT: Base](self, name: str, service_type: type[ServiceT]) -> ServiceT:
        """Return the named service, building it on first access.

        Args:
            name: The registry key.
            service_type: The expected class, which is also the caller's return type.

        Returns:
            The cached service instance.

        Raises:
            RuntimeError: If accessed outside the context manager.
            KeyError: If the registry has no such service.
            TypeError: If the registry maps the name to a different class.
        """
        if self._session is None:
            raise RuntimeError(_OUTSIDE_CONTEXT)

        cached = self._services.get(name)
        if cached is not None:
            if not isinstance(cached, service_type):
                raise TypeError(
                    f"Service {name!r} is a {type(cached).__name__}, expected "
                    f"{service_type.__name__}."
                )
            return cached

        config = self._registry[name]
        if not issubclass(config.service_class, service_type):
            raise TypeError(
                f"Registry maps {name!r} to {config.service_class.__name__}, expected "
                f"{service_type.__name__}."
            )

        service = config.service_class(
            self._session,
            config.base_url,
            self.auth,
            config.limiter,
            max_retry_attempts=self._max_retry_attempts,
            max_retry_wait_seconds=self._max_retry_wait_seconds,
        )
        self._services[name] = service
        return service
