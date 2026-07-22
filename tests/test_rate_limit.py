"""The composite limiter covering Strava's two quota windows."""

import asyncio
from types import TracebackType

import pytest
from aiolimiter import AsyncLimiter

from strava_async.rate_limit import (
    DAY_SECONDS,
    QUARTER_HOUR_SECONDS,
    CompositeLimiter,
    build_rate_limiter,
)


class RecordingLimiter:
    """Records enter/exit order, and can be told to fail on entry."""

    def __init__(self, name: str, log: list[str], *, fail: bool = False) -> None:
        self.name = name
        self._log = log
        self._fail = fail

    async def __aenter__(self) -> None:
        if self._fail:
            self._log.append(f"{self.name}:fail")
            raise RuntimeError(f"{self.name} refused")
        self._log.append(f"{self.name}:enter")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._log.append(f"{self.name}:exit")


def test_build_covers_both_windows() -> None:
    limiter = build_rate_limiter(requests_per_quarter_hour=100, daily_request_limit=1000)

    assert [(inner.max_rate, inner.time_period) for inner in limiter.limiters] == [
        (100, QUARTER_HOUR_SECONDS),
        (1000, DAY_SECONDS),
    ]


def test_shortest_window_is_checked_first() -> None:
    """A burst should be stopped by the cheapest check before it touches the day's budget."""
    limiter = build_rate_limiter(requests_per_quarter_hour=100, daily_request_limit=1000)

    assert limiter.limiters[0].time_period < limiter.limiters[1].time_period


async def test_acquires_every_limiter_in_order() -> None:
    log: list[str] = []
    limiter = CompositeLimiter(
        [RecordingLimiter("short", log), RecordingLimiter("daily", log)]  # ty: ignore[invalid-argument-type]
    )

    async with limiter:
        log.append("request")

    assert log == ["short:enter", "daily:enter", "request", "daily:exit", "short:exit"]


async def test_releases_what_it_acquired_when_a_later_limiter_fails() -> None:
    """A part-way failure must not leak the slots already taken."""
    log: list[str] = []
    limiter = CompositeLimiter(
        [  # ty: ignore[invalid-argument-type]
            RecordingLimiter("short", log),
            RecordingLimiter("daily", log, fail=True),
        ]
    )

    with pytest.raises(RuntimeError, match="daily refused"):
        async with limiter:
            log.append("request")

    assert log == ["short:enter", "daily:fail", "short:exit"]
    assert "request" not in log


async def test_a_real_limiter_admits_up_to_its_budget_without_waiting() -> None:
    """Sanity check against the real AsyncLimiter, not just the double."""
    limiter = CompositeLimiter([AsyncLimiter(3, QUARTER_HOUR_SECONDS)])

    async with asyncio.timeout(1):
        for _ in range(3):
            async with limiter:
                pass


async def test_the_daily_budget_can_bind_before_the_short_one() -> None:
    """The point of the composite: a generous short window does not bypass the day's cap."""
    limiter = CompositeLimiter(
        [AsyncLimiter(1000, QUARTER_HOUR_SECONDS), AsyncLimiter(2, DAY_SECONDS)]
    )

    async with asyncio.timeout(1):
        async with limiter:
            pass
        async with limiter:
            pass

    # The third acquisition would block on the daily limiter for hours.
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.05):
            async with limiter:
                pass
