"""HTTP API schemas for AeroRAG-X."""

from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class HealthResponse(BaseModel):
    """Basic process-health response."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str


class ReadinessResponse(BaseModel):
    """Application readiness response."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: str
    ready: bool


class QueryRequest(BaseModel):
    """Grounded-query API request."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=1,
        max_length=2000,
    )
