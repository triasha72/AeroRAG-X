"""Recorded behavior used by deterministic reward functions."""

from pydantic import BaseModel, ConfigDict, Field


class GroundedRolloutRecord(BaseModel):
    """One completed rollout summarized without hidden reasoning."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=1)
    answer: str | None = None
    refused: bool
    cited_evidence_ids: list[str] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)
    tool_call_count: int = Field(ge=0)
    structured_output_valid: bool
    evidence_supported: bool
