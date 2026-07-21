"""The request pipeline every service delegates to.

All network I/O funnels through here: auth, rate limiting, retries, status-to-exception
mapping, and response validation. Services never touch the session directly — doing so
would skip all five.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, BinaryIO

import aiohttp
from aiolimiter import AsyncLimiter
from pydantic import BaseModel, TypeAdapter
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception_type, stop_after_attempt
from tenacity.wait import wait_exponential

from strava_async.exceptions import (
    StravaAuthenticationError,
    StravaConnectionError,
    StravaRateLimitError,
    map_status_code_to_exception,
)
from strava_async.protocols import AuthClientProtocol

__all__ = ["Base"]

_QUARTER_HOUR_SECONDS = 15 * 60

# Rebuilding a TypeAdapter per call is measurable on list endpoints; the key is the
# annotation itself, and `list[X] == list[X]`, so generics cache correctly too.
_ADAPTERS: dict[Any, TypeAdapter[Any]] = {}


def _adapter_for(model: Any) -> TypeAdapter[Any]:
    if model not in _ADAPTERS:
        _ADAPTERS[model] = TypeAdapter(model)
    return _ADAPTERS[model]


def _encode_value(value: Any) -> str:
    """Render a JSON-safe scalar the way aiohttp's query encoder needs it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _seconds_until_next_quarter_hour(now: datetime) -> float:
    """Seconds remaining in the current 15-minute rate-limit window."""
    elapsed = (now.minute % 15) * 60 + now.second + now.microsecond / 1_000_000
    return _QUARTER_HOUR_SECONDS - elapsed


class Base:
    """Shared transport for every service.

    Args:
        session: The session owned by the client.
        base_url: Root URL for this service's endpoints.
        auth_client: Supplies and invalidates the OAuth token.
        limiter: The app-wide rate limiter. Every service shares one instance — Strava's
            quota is per application, not per endpoint family.
        max_retry_attempts: Total attempts, including the first.
        max_retry_wait_seconds: Ceiling on any single backoff. Caps a 429 whose window is
            fifteen minutes from resetting.
        sleep: How to wait between attempts. Injectable so tests assert the computed
            backoff instead of spending it.
        now: Clock used to work out when the current rate-limit window resets.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        auth_client: AuthClientProtocol,
        limiter: AsyncLimiter,
        *,
        max_retry_attempts: int = 4,
        max_retry_wait_seconds: float = 60.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session = session
        self.base_url = base_url
        self._auth_client = auth_client
        self._limiter = limiter
        self._max_retry_attempts = max_retry_attempts
        self._max_retry_wait_seconds = max_retry_wait_seconds
        self._sleep = sleep
        self._now = now

    async def fetch_data(
        self,
        *,
        endpoint: str,
        model: Any,
        method: str = "GET",
        params: BaseModel | None = None,
        payload: BaseModel | None = None,
        error_endpoint: str | None = None,
        uses_oauth: bool = True,
    ) -> Any:
        """Issue a request and validate the JSON response into ``model``.

        Args:
            endpoint: Fully-qualified URL.
            model: A Pydantic model, or a generic alias such as ``list[SummaryActivity]``.
            method: HTTP verb.
            params: Query parameters, as a model.
            payload: JSON request body, as a model.
            error_endpoint: Redacted URL to attach to exceptions, when the real one
                embeds a secret.
            uses_oauth: False for endpoints authenticated some other way, so a 401 there
                never churns the shared token.

        Returns:
            The response body validated into ``model``.
        """
        body = await self._request(
            method=method,
            endpoint=endpoint,
            params=params,
            json_body=_dump(payload),
            read="json",
            error_endpoint=error_endpoint,
            uses_oauth=uses_oauth,
        )
        return _adapter_for(model).validate_python(body)

    async def _post_form(
        self, *, endpoint: str, model: Any, payload: BaseModel | None = None
    ) -> Any:
        """POST form-encoded fields and validate the JSON response into ``model``."""
        body = await self._request(
            method="POST", endpoint=endpoint, form_body=_dump(payload), read="json"
        )
        return _adapter_for(model).validate_python(body)

    async def _put_form(
        self, *, endpoint: str, model: Any, payload: BaseModel | None = None
    ) -> Any:
        """PUT form-encoded fields and validate the JSON response into ``model``."""
        body = await self._request(
            method="PUT", endpoint=endpoint, form_body=_dump(payload), read="json"
        )
        return _adapter_for(model).validate_python(body)

    async def _post_multipart(
        self,
        *,
        endpoint: str,
        model: Any,
        payload: BaseModel | None = None,
        file: BinaryIO | bytes,
        filename: str = "upload",
    ) -> Any:
        """POST a file plus form fields, validating the JSON response into ``model``."""
        form = aiohttp.FormData()
        for key, value in (_dump(payload) or {}).items():
            form.add_field(key, _encode_value(value))
        form.add_field("file", file, filename=filename)

        body = await self._request(
            method="POST", endpoint=endpoint, multipart_body=form, read="json"
        )
        return _adapter_for(model).validate_python(body)

    async def _delete(self, *, endpoint: str) -> None:
        """DELETE a resource that returns no body."""
        await self._request(method="DELETE", endpoint=endpoint, read="none")

    async def _get_text(self, *, endpoint: str, params: BaseModel | None = None) -> str:
        """GET a text or XML response, such as a GPX or TCX export."""
        return await self._request(method="GET", endpoint=endpoint, params=params, read="text")

    async def _get_bytes(self, *, endpoint: str, params: BaseModel | None = None) -> bytes:
        """GET a binary response."""
        return await self._request(method="GET", endpoint=endpoint, params=params, read="bytes")

    async def _request(
        self,
        *,
        method: str,
        endpoint: str,
        params: BaseModel | None = None,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, Any] | None = None,
        multipart_body: aiohttp.FormData | None = None,
        read: str = "json",
        error_endpoint: str | None = None,
        uses_oauth: bool = True,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Run one request through the full pipeline, retrying transient failures."""
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_retry_attempts),
            wait=self._wait,
            retry=retry_if_exception_type(
                (StravaConnectionError, StravaAuthenticationError, StravaRateLimitError)
            ),
            sleep=self._sleep,
            reraise=True,
        )
        return await retrying(
            self._send,
            method=method,
            endpoint=endpoint,
            params=params,
            json_body=json_body,
            form_body=form_body,
            multipart_body=multipart_body,
            read=read,
            error_endpoint=error_endpoint,
            uses_oauth=uses_oauth,
            headers=headers,
        )

    async def _send(
        self,
        *,
        method: str,
        endpoint: str,
        params: BaseModel | None,
        json_body: dict[str, Any] | None,
        form_body: dict[str, Any] | None,
        multipart_body: aiohttp.FormData | None,
        read: str,
        error_endpoint: str | None,
        uses_oauth: bool,
        headers: dict[str, str] | None,
    ) -> Any:
        """One attempt: authenticate, wait for a slot, send, map errors, read."""
        reported_endpoint = error_endpoint or endpoint

        request_headers = dict(headers) if headers else {}
        if headers is None and uses_oauth:
            request_headers = await self._auth_client.get_headers()

        query = _encode_params(params)
        data: Any = multipart_body if multipart_body is not None else form_body

        try:
            async with (
                self._limiter,
                self._session.request(
                    method,
                    endpoint,
                    params=query,
                    json=json_body,
                    data=data,
                    headers=request_headers,
                ) as response,
            ):
                raw = await _read_body(response, read)
                if response.status >= 400:
                    self._raise_for_status(
                        status=response.status,
                        response_headers=response.headers,
                        endpoint=reported_endpoint,
                        body=raw,
                        uses_oauth=uses_oauth,
                    )
                return raw
        except aiohttp.ClientError as exc:
            raise StravaConnectionError(
                f"Request to Strava failed: {exc}", endpoint=reported_endpoint
            ) from exc
        except TimeoutError as exc:
            raise StravaConnectionError(
                "Request to Strava timed out.", endpoint=reported_endpoint
            ) from exc

    def _raise_for_status(
        self,
        *,
        status: int,
        response_headers: Any,
        endpoint: str,
        body: Any,
        uses_oauth: bool,
    ) -> None:
        """Map an error status onto the exception hierarchy and raise it."""
        details = body if isinstance(body, dict) else {"body": body}
        message = str(details.get("message") or "Strava rejected the request.")
        exception_class = map_status_code_to_exception(status)

        if status == 429:
            raise StravaRateLimitError(
                message,
                retry_after=_retry_after_seconds(response_headers, self._now()),
                status_code=status,
                endpoint=endpoint,
                details=details | _rate_limit_details(response_headers),
            )

        # Only churn the shared token when the request actually used it. A 401 from an
        # endpoint authenticated some other way says nothing about our OAuth token.
        if status == 401 and uses_oauth:
            self._auth_client.invalidate_token()

        raise exception_class(message, status_code=status, endpoint=endpoint, details=details)

    def _wait(self, retry_state: RetryCallState) -> float:
        """Honour a rate-limit hint when there is one, else back off exponentially."""
        exception = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(exception, StravaRateLimitError) and exception.retry_after is not None:
            return min(exception.retry_after, self._max_retry_wait_seconds)
        return wait_exponential(multiplier=1, max=self._max_retry_wait_seconds)(retry_state)


def _dump(model: BaseModel | None) -> dict[str, Any] | None:
    """Serialize a request model exactly one way, everywhere."""
    if model is None:
        return None
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def _encode_params(params: BaseModel | None) -> dict[str, str] | None:
    """Serialize a params model into what aiohttp accepts as a query string."""
    dumped = _dump(params)
    if not dumped:
        return None
    return {key: _encode_value(value) for key, value in dumped.items()}


async def _read_body(response: aiohttp.ClientResponse, read: str) -> Any:
    """Read the response in the shape the caller asked for.

    Error bodies are always JSON regardless of what the endpoint normally returns, so a
    failing text or binary endpoint still yields a parsed fault.
    """
    if response.status >= 400:
        try:
            return await response.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError):
            return await response.text()
    if read == "json":
        return await response.json(content_type=None)
    if read == "text":
        return await response.text()
    if read == "bytes":
        return await response.read()
    return None


def _retry_after_seconds(headers: Any, now: datetime) -> float:
    """How long to wait after a 429.

    Strava does not reliably send ``Retry-After``, so fall back to the time left in the
    current quarter-hour window, which is when the short-term budget resets.
    """
    raw = headers.get("Retry-After") if hasattr(headers, "get") else None
    if raw is not None:
        try:
            return float(raw)
        except ValueError:
            pass
    return _seconds_until_next_quarter_hour(now)


def _rate_limit_details(headers: Any) -> dict[str, Any]:
    """Pull Strava's usage headers onto the exception so callers can self-throttle."""
    if not hasattr(headers, "get"):
        return {}
    keys = (
        "X-RateLimit-Limit",
        "X-RateLimit-Usage",
        "X-ReadRateLimit-Limit",
        "X-ReadRateLimit-Usage",
    )
    return {key: headers.get(key) for key in keys if headers.get(key) is not None}
