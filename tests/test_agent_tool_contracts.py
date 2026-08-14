"""Tests for typed Phase 36 agent-tool contracts."""

import pytest
from pydantic import ValidationError

from aeroragx.agent.contracts import (
    EvidenceReference,
    SourceComparisonRecord,
    ToolCallRecord,
)


def test_tool_call_requires_error_metadata_on_failure() -> None:
    with pytest.raises(ValidationError, match="Failed tool calls"):
        ToolCallRecord(
            tool_call_id="call-1",
            tool_name="hybrid_retrieve",
            status="error",
            latency_ms=1.0,
        )


def test_evidence_reference_rejects_inverted_page_range() -> None:
    with pytest.raises(ValidationError, match="page_end"):
        EvidenceReference(
            evidence_id="e-1",
            document_id=123,
            page_start=10,
            page_end=9,
        )


def test_source_comparison_requires_two_documents() -> None:
    with pytest.raises(ValidationError, match="two distinct documents"):
        SourceComparisonRecord(
            comparison_id="cmp-1",
            evidence_ids=["e-1", "e-2"],
            document_ids=[123, 123],
            summary="Same document only.",
            conflict_detected=False,
        )
