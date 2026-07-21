"""Shared model bases.

Responses tolerate unknown fields, because Strava adds them without notice and a strict
model would turn a harmless addition into a client-wide outage. Requests forbid them, so
a typo fails at construction instead of being silently dropped on the wire.
"""

from pydantic import BaseModel, ConfigDict

__all__ = ["RequestModel", "ResponseModel"]


class ResponseModel(BaseModel):
    """Base for everything Strava sends us."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore", frozen=True)


class RequestModel(BaseModel):
    """Base for everything we send Strava."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")
