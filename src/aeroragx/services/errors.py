"""Structured service error envelopes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ServiceErrorCode = Literal[
    "timeout",
    "dependency_unavailable",
    "invalid_request",
    "invalid_response",
    "internal_error",
]


class ServiceErrorEnvelope(BaseModel):
    """Stable error shape for cross-service failures."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: ServiceErrorCode
    message: str = Field(min_length=1, max_length=500)
    retryable: bool
