"""Service name to (class, base URL, limiter).

Adding a service is an entry here plus a property on the client.
"""

from dataclasses import dataclass

from aiolimiter import AsyncLimiter

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
from strava_async.settings import StravaSettings

__all__ = ["ServiceConfig", "ServiceRegistry", "build_service_registry"]

_QUARTER_HOUR_SECONDS = 15 * 60

_SERVICE_CLASSES: dict[str, type[Base]] = {
    "activities": ActivitiesService,
    "athletes": AthletesService,
    "clubs": ClubsService,
    "gear": GearService,
    "routes": RoutesService,
    "segment_efforts": SegmentEffortsService,
    "segments": SegmentsService,
    "streams": StreamsService,
    "uploads": UploadsService,
}


@dataclass(frozen=True)
class ServiceConfig:
    """Everything needed to construct one service."""

    service_class: type[Base]
    base_url: str
    limiter: AsyncLimiter


type ServiceRegistry = dict[str, ServiceConfig]


def build_service_registry(settings: StravaSettings) -> ServiceRegistry:
    """Build the registry from configuration.

    Every entry shares one base URL and — importantly — one limiter instance. Strava's
    quota is per application, so giving each service its own limiter would multiply the
    effective request rate by the number of services and get the app throttled.

    Args:
        settings: Configuration supplying the base URL and the rate budget.

    Returns:
        A mapping of service name to its configuration.
    """
    limiter = AsyncLimiter(settings.requests_per_quarter_hour, _QUARTER_HOUR_SECONDS)
    return {
        name: ServiceConfig(
            service_class=service_class,
            base_url=settings.base_url,
            limiter=limiter,
        )
        for name, service_class in _SERVICE_CLASSES.items()
    }
