"""Pydantic contracts for Agent, Retrieval, and Inference services."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.services.request_context import RequestContext


class ServiceEvidence(BaseModel):
    """Provenance-preserving evidence transferred between services."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1)
    document_id: int = Field(ge=1)
    text: str = Field(min_length=1)
    citation_url: str = Field(min_length=1)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    score: float | None = None


class RetrievalServiceRequest(BaseModel):
    """Retrieval request sent by the agent service."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    context: RequestContext
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)


class RetrievalServiceResponse(BaseModel):
    """Retrieval response containing only explicit evidence records."""

    model_config = ConfigDict(extra="forbid")

    context: RequestContext
    evidence: list[ServiceEvidence] = Field(default_factory=list)


class InferenceServiceRequest(BaseModel):
    """Grounded generation request."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    context: RequestContext
    query: str = Field(min_length=1)
    evidence: list[ServiceEvidence] = Field(min_length=1)
    max_new_tokens: int = Field(default=256, ge=1, le=4096)


class InferenceServiceResponse(BaseModel):
    """Candidate answer returned by the inference service."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    context: RequestContext
    answer: str = Field(min_length=1)
    cited_evidence_ids: list[str] = Field(default_factory=list)


class AgentServiceRequest(BaseModel):
    """External request accepted by the distributed Agent API."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    context: RequestContext
    query: str = Field(min_length=1)


class AgentServiceResponse(BaseModel):
    """Terminal distributed Agent API response."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    context: RequestContext
    answer: str | None = None
    cited_evidence_ids: list[str] = Field(default_factory=list)
    termination_reason: str = Field(min_length=1)
