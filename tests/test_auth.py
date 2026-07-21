"""Token refresh, caching, rotation, and invalidation."""

import asyncio

import aiohttp
import pytest

from strava_async.auth.client import StravaAuthClient
from strava_async.exceptions import StravaAuthenticationError, StravaConnectionError
from tests.conftest import FakeResponse

TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"


class FakeTokenSession:
    """Serves scripted token responses and records the bodies posted."""

    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self._responses = list(responses)
        self.posts: list[dict[str, str]] = []

    def post(self, url: str, data: dict[str, str] | None = None, **_: object):
        self.posts.append(dict(data or {}))
        response = self._responses.pop(0)

        class _Context:
            async def __aenter__(self) -> FakeResponse:
                if isinstance(response, Exception):
                    raise response
                return response

            async def __aexit__(self, *_: object) -> None:
                return None

        return _Context()


def token_body(access_token: str = "access-1", expires_at: float = 10_000.0, **extra: object):
    return {"access_token": access_token, "expires_at": expires_at, **extra}


def make_client(session: FakeTokenSession, *, now: float = 0.0, **kwargs: object):
    return StravaAuthClient(
        session,  # ty: ignore[invalid-argument-type]
        client_id="123",
        client_secret="shh",
        refresh_token="refresh-0",
        token_url=TOKEN_URL,
        now=lambda: now,
        **kwargs,  # ty: ignore[invalid-argument-type]
    )


async def test_exchanges_the_refresh_token() -> None:
    session = FakeTokenSession(FakeResponse(json_body=token_body()))
    client = make_client(session)

    assert await client.get_access_token() == "access-1"
    assert session.posts[0] == {
        "client_id": "123",
        "client_secret": "shh",
        "grant_type": "refresh_token",
        "refresh_token": "refresh-0",
    }


async def test_returns_the_authorization_header() -> None:
    session = FakeTokenSession(FakeResponse(json_body=token_body()))
    client = make_client(session)

    assert await client.get_headers() == {"Authorization": "Bearer access-1"}


async def test_caches_the_token() -> None:
    session = FakeTokenSession(FakeResponse(json_body=token_body()))
    client = make_client(session)

    await client.get_access_token()
    await client.get_access_token()

    assert len(session.posts) == 1


async def test_concurrent_callers_trigger_one_exchange() -> None:
    """The lock plus the re-check inside it is what prevents a token stampede."""
    session = FakeTokenSession(FakeResponse(json_body=token_body()))
    client = make_client(session)

    tokens = await asyncio.gather(*[client.get_access_token() for _ in range(10)])

    assert tokens == ["access-1"] * 10
    assert len(session.posts) == 1


async def test_refreshes_within_the_expiry_margin() -> None:
    """A token expiring inside the margin is treated as already stale."""
    session = FakeTokenSession(
        FakeResponse(json_body=token_body("access-1", expires_at=100.0)),
        FakeResponse(json_body=token_body("access-2", expires_at=10_000.0)),
    )
    client = make_client(session, now=0.0, expiry_margin_seconds=300.0)

    assert await client.get_access_token() == "access-1"
    assert await client.get_access_token() == "access-2"


async def test_invalidate_forces_a_refetch() -> None:
    session = FakeTokenSession(
        FakeResponse(json_body=token_body("access-1")),
        FakeResponse(json_body=token_body("access-2")),
    )
    client = make_client(session)

    assert await client.get_access_token() == "access-1"
    client.invalidate_token()
    assert await client.get_access_token() == "access-2"


async def test_captures_a_rotated_refresh_token() -> None:
    """Strava rotates refresh tokens; dropping the new one strands the credential."""
    rotated: list[str] = []
    session = FakeTokenSession(FakeResponse(json_body=token_body(refresh_token="refresh-1")))
    client = make_client(session, on_token_refresh=rotated.append)

    await client.get_access_token()

    assert client.refresh_token == "refresh-1"
    assert rotated == ["refresh-1"]


async def test_reuses_the_refresh_token_when_not_rotated() -> None:
    session = FakeTokenSession(FakeResponse(json_body=token_body(refresh_token="refresh-0")))
    rotated: list[str] = []
    client = make_client(session, on_token_refresh=rotated.append)

    await client.get_access_token()

    assert client.refresh_token == "refresh-0"
    assert rotated == []


async def test_maps_a_rejected_exchange_to_an_auth_error() -> None:
    session = FakeTokenSession(FakeResponse(status=401, json_body={"message": "Bad credentials"}))
    client = make_client(session)

    with pytest.raises(StravaAuthenticationError) as caught:
        await client.get_access_token()

    assert caught.value.status_code == 401


async def test_never_leaks_the_client_secret_in_errors() -> None:
    session = FakeTokenSession(FakeResponse(status=400, json_body={"message": "bad"}))
    client = make_client(session)

    with pytest.raises(Exception) as caught:
        await client.get_access_token()

    assert "shh" not in str(caught.value)
    assert caught.value.endpoint == "POST /oauth/token"  # ty: ignore[unresolved-attribute]


async def test_maps_transport_failure_to_a_connection_error() -> None:
    session = FakeTokenSession(aiohttp.ClientConnectionError("dns"))
    client = make_client(session)

    with pytest.raises(StravaConnectionError):
        await client.get_access_token()
