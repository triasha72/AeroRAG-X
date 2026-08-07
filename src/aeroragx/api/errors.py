"""Structured HTTP errors for the AeroRAG-X API."""

from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ApiErrorDetail(BaseModel):
    """Machine-readable API error details."""

    model_config = ConfigDict(
        extra="forbid",
    )

    code: str = Field(
        min_length=1,
    )

    message: str = Field(
        min_length=1,
    )

    request_id: str = Field(
        min_length=1,
    )


class ApiErrorResponse(BaseModel):
    """Stable API error response envelope."""

    model_config = ConfigDict(
        extra="forbid",
    )

    error: ApiErrorDetail


class RuntimeUnavailableError(RuntimeError):
    """Raised when the query runtime is unavailable."""
