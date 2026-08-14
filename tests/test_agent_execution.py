"""Tests for Phase 37 execution result contracts."""

import pytest
from pydantic import ValidationError

from aeroragx.agent.contracts import ToolCallRecord
from aeroragx.agent.execution import ToolExecutionResult


def test_tool_execution_rejects_duplicate_evidence_ids() -> None:
    call = ToolCallRecord(
        tool_call_id="call-1",
        tool_name="hybrid_retrieve",
        status="success",
        latency_ms=1.0,
    )
    with pytest.raises(ValidationError, match="evidence_ids"):
        ToolExecutionResult(
            call=call,
            evidence_ids=["e1", "e1"],
        )
