"""Strava's error envelope.

Every non-2xx response body follows this shape, and the pipeline puts it on the raised
exception's ``details`` as a plain dict. This model is for callers who want it typed:
``Fault.model_validate(error.details)``.
"""

from pydantic import Field

from strava_async.schemas.base import ResponseModel

__all__ = ["Error", "Fault"]


class Error(ResponseModel):
    """A single thing Strava objected to."""

    code: str | None = None
    field: str | None = None
    resource: str | None = None


class Fault(ResponseModel):
    """The body of a failed request."""

    message: str | None = None
    errors: list[Error] = Field(default_factory=list)
