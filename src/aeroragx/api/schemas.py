"""HTTP API schemas for AeroRAG-X."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


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
