"""Rate limiting across Strava's two quota windows.

Strava budgets requests over a short window and a daily one at the same time, and both
are per application rather than per endpoint. A single limiter can only model one of
them, so this module composes several and requires a slot in every one before a request
proceeds.
"""

from collections.abc import Iterable
from types import TracebackType

from aiolimiter import AsyncLimiter

__all__ = ["DAY_SECONDS", "QUARTER_HOUR_SECONDS", "CompositeLimiter", "build_rate_limiter"]

QUARTER_HOUR_SECONDS = 15 * 60
DAY_SECONDS = 24 * 60 * 60


class CompositeLimiter:
    """Acquires a slot in every underlying limiter before yielding.

    Entering is ordered, and a failure part-way through releases whatever was already
    acquired, so a cancelled request cannot leak a slot.

    Args:
        limiters: The limiters to acquire, in order. Put the shortest window first so a
            burst is stopped by the cheapest check.
    """

    def __init__(self, limiters: Iterable[AsyncLimiter]) -> None:
        self._limiters = tuple(limiters)

    @property
    def limiters(self) -> tuple[AsyncLimiter, ...]:
        """The underlying limiters, shortest window first."""
        return self._limiters

    async def __aenter__(self) -> None:
        acquired: list[AsyncLimiter] = []
        try:
            for limiter in self._limiters:
                await limiter.__aenter__()
                acquired.append(limiter)
        except BaseException:
            for limiter in reversed(acquired):
                await limiter.__aexit__(None, None, None)
            raise

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        for limiter in reversed(self._limiters):
            await limiter.__aexit__(exc_type, exc, tb)


def build_rate_limiter(
    *, requests_per_quarter_hour: int, daily_request_limit: int
) -> CompositeLimiter:
    """Build the app-wide limiter covering both of Strava's windows.

    Args:
        requests_per_quarter_hour: The short-window budget.
        daily_request_limit: The 24-hour budget.

    Returns:
        A limiter that enforces both budgets at once.
    """
    return CompositeLimiter(
        [
            AsyncLimiter(requests_per_quarter_hour, QUARTER_HOUR_SECONDS),
            AsyncLimiter(daily_request_limit, DAY_SECONDS),
        ]
    )
