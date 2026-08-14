"""Typed contracts for bounded AeroRAG-X agent tools."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

AgentToolName = Literal[
    "hybrid_retrieve",
    "fetch_source_context",
    "check_evidence_sufficiency",
    "validate_citations",
    "compare_sources",
]
ToolStatus = Literal["success", "error"]
ToolErrorCode = Literal[
    "backend_error",
    "invalid_result",
]


class AgentToolError(BaseModel):
    """Structured tool failure returned to the future agent graph."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: ToolErrorCode
    message: str = Field(min_length=1, max_length=500)


class ToolCallRecord(BaseModel):
    """Common execution metadata for one bounded tool call."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tool_call_id: str = Field(min_length=1)
    tool_name: AgentToolName
    status: ToolStatus
    latency_ms: float = Field(ge=0.0)
    error: AgentToolError | None = None

    @model_validator(mode="after")
    def validate_status_error_pair(self) -> Self:
        """Require error metadata exactly when the call failed."""

        if self.status == "success" and self.error is not None:
            raise ValueError("Successful tool calls must not include an error.")
        if self.status == "error" and self.error is None:
            raise ValueError("Failed tool calls must include an error.")
        return self


class EvidenceReference(BaseModel):
    """Minimal provenance-preserving evidence reference returned by retrieval."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1)
    document_id: int = Field(ge=1)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    citation_url: str | None = None
    score: float | None = None

    @model_validator(mode="after")
    def validate_page_range(self) -> Self:
        """Reject inverted page ranges."""

        if (
            self.page_start is not None
            and self.page_end is not None
            and self.page_end < self.page_start
        ):
            raise ValueError("page_end must be greater than or equal to page_start.")
        return self


class SourceContextRecord(BaseModel):
    """Authoritative source context associated with one evidence identifier."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_id: str = Field(min_length=1)
    document_id: int = Field(ge=1)
    text: str = Field(min_length=1)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    source_url: str = Field(min_length=1)
    citation_url: str = Field(min_length=1)
    document_sha256: str = Field(min_length=1)


class SufficiencyAssessment(BaseModel):
    """Backend-neutral evidence-sufficiency result for agent routing."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sufficient: bool
    reasons: list[str] = Field(default_factory=list)
    coverage: float | None = Field(default=None, ge=0.0, le=1.0)


class SourceComparisonRecord(BaseModel):
    """Structured comparison record derived from multiple evidence sources."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    comparison_id: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=2)
    document_ids: list[int] = Field(min_length=2)
    summary: str = Field(min_length=1)
    conflict_detected: bool

    @model_validator(mode="after")
    def validate_distinct_sources(self) -> Self:
        """Require a comparison to span at least two unique documents."""

        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("comparison evidence_ids must be unique.")
        if len(set(self.document_ids)) < 2:
            raise ValueError("source comparison requires at least two distinct documents.")
        return self


class HybridRetrieveRequest(BaseModel):
    """Input contract for the hybrid retrieval tool."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)


class HybridRetrieveResult(BaseModel):
    """Output contract for the hybrid retrieval tool."""

    model_config = ConfigDict(extra="forbid")

    call: ToolCallRecord
    query: str = Field(min_length=1)
    evidence: list[EvidenceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_tool_identity(self) -> Self:
        if self.call.tool_name != "hybrid_retrieve":
            raise ValueError("HybridRetrieveResult requires hybrid_retrieve call metadata.")
        return self


class FetchSourceContextRequest(BaseModel):
    """Input contract for authoritative source-context lookup."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique.")
        return self


class FetchSourceContextResult(BaseModel):
    """Output contract for source-context lookup."""

    model_config = ConfigDict(extra="forbid")

    call: ToolCallRecord
    contexts: list[SourceContextRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_tool_identity(self) -> Self:
        if self.call.tool_name != "fetch_source_context":
            raise ValueError(
                "FetchSourceContextResult requires fetch_source_context call metadata."
            )
        return self


class CheckEvidenceSufficiencyRequest(BaseModel):
    """Input contract for evidence-sufficiency assessment."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique.")
        return self


class CheckEvidenceSufficiencyResult(BaseModel):
    """Output contract for evidence-sufficiency assessment."""

    model_config = ConfigDict(extra="forbid")

    call: ToolCallRecord
    assessment: SufficiencyAssessment | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> Self:
        if self.call.tool_name != "check_evidence_sufficiency":
            raise ValueError(
                "CheckEvidenceSufficiencyResult requires check_evidence_sufficiency call metadata."
            )
        if self.call.status == "success" and self.assessment is None:
            raise ValueError("Successful sufficiency calls require an assessment.")
        if self.call.status == "error" and self.assessment is not None:
            raise ValueError("Failed sufficiency calls must not include an assessment.")
        return self


class ValidateCitationsRequest(BaseModel):
    """Input contract for deterministic evidence-ID citation validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    cited_evidence_ids: list[str]
    known_evidence_ids: list[str]

    @model_validator(mode="after")
    def validate_known_ids(self) -> Self:
        if len(set(self.known_evidence_ids)) != len(self.known_evidence_ids):
            raise ValueError("known_evidence_ids must be unique.")
        return self


class ValidateCitationsResult(BaseModel):
    """Output contract for deterministic citation validation."""

    model_config = ConfigDict(extra="forbid")

    call: ToolCallRecord
    valid: bool
    unknown_evidence_ids: list[str] = Field(default_factory=list)
    duplicate_evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_tool_identity(self) -> Self:
        if self.call.tool_name != "validate_citations":
            raise ValueError("ValidateCitationsResult requires validate_citations call metadata.")
        expected_valid = (
            self.call.status == "success"
            and not self.unknown_evidence_ids
            and not self.duplicate_evidence_ids
        )
        if self.valid != expected_valid:
            raise ValueError("valid must reflect call status, unknown IDs, and duplicate IDs.")
        return self


class CompareSourcesRequest(BaseModel):
    """Input contract for structured source comparison."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evidence_ids: list[str] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> Self:
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids must be unique.")
        return self


class CompareSourcesResult(BaseModel):
    """Output contract for structured source comparison."""

    model_config = ConfigDict(extra="forbid")

    call: ToolCallRecord
    comparisons: list[SourceComparisonRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_tool_identity(self) -> Self:
        if self.call.tool_name != "compare_sources":
            raise ValueError("CompareSourcesResult requires compare_sources call metadata.")
        return self
