"""Structural types for injected collaborators.

This module deliberately imports nothing from the package. Higher layers depend on these
Protocols rather than on concrete classes, which keeps ``client.py`` substitutable and
lets tests supply doubles without patching.
"""

from types import TracebackType
from typing import Protocol, runtime_checkable

import aiohttp

__all__ = ["AuthClientFactory", "AuthClientProtocol", "RateLimiterProtocol"]


@runtime_checkable
class AuthClientProtocol(Protocol):
    """What the request pipeline needs from an auth client."""

    async def get_headers(self) -> dict[str, str]:
        """Return the headers that authenticate a request, refreshing if needed."""
        ...

    def invalidate_token(self) -> None:
        """Drop the cached access token so the next call re-fetches it."""
        ...


class AuthClientFactory(Protocol):
    """Builds an auth client once the client owns a session.

    The parameter is positional-only so any single-argument callable satisfies this,
    regardless of what it names its argument.
    """

    def __call__(self, session: aiohttp.ClientSession, /) -> AuthClientProtocol:
        """Return an auth client bound to ``session``."""
        ...


class RateLimiterProtocol(Protocol):
    """An async context manager that yields once a request slot is available."""

    async def __aenter__(self) -> None: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
