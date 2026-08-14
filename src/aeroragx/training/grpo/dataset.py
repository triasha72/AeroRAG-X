"""Frozen training-case contract for grounded tool-use post-training."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.services.contracts import ServiceEvidence


class GroundedAgentTrainingCase(BaseModel):
    """One post-training case with precomputed evidence and answerability."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    answerable: bool
    evidence: list[ServiceEvidence] = Field(default_factory=list)
    reference_answer: str | None = None
    expected_citation_ids: list[str] = Field(default_factory=list)
