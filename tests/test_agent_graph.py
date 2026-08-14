"""Integration-style tests for the Phase 37 stateful graph."""

from aeroragx.agent.contracts import ToolCallRecord
from aeroragx.agent.execution import (
    CitationValidationResult,
    GenerationResult,
    ToolExecutionResult,
)
from aeroragx.agent.graph import StatefulAgentGraph
from aeroragx.agent.planner import DeterministicEvidencePlanner
from aeroragx.agent.registry import build_default_agent_tool_registry
from aeroragx.agent.state import AgentState


class Executor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, tool_name, state):  # type: ignore[no-untyped-def]
        self.calls += 1
        if tool_name == "hybrid_retrieve":
            return ToolExecutionResult(
                call=ToolCallRecord(
                    tool_call_id=f"call-{self.calls}",
                    tool_name=tool_name,
                    status="success",
                    latency_ms=1.0,
                ),
                evidence_ids=["e1"],
                document_ids=[123],
            )
        return ToolExecutionResult(
            call=ToolCallRecord(
                tool_call_id=f"call-{self.calls}",
                tool_name=tool_name,
                status="success",
                latency_ms=1.0,
            ),
            evidence_sufficient=True,
        )


class Generator:
    def generate(self, state):  # type: ignore[no-untyped-def]
        return GenerationResult(answer="grounded answer", cited_evidence_ids=["e1"])


class Validator:
    def validate(self, generation, state):  # type: ignore[no-untyped-def]
        return CitationValidationResult(valid=True)


def test_stateful_graph_retrieves_assesses_generates_and_finishes() -> None:
    result = StatefulAgentGraph(
        planner=DeterministicEvidencePlanner(),
        tool_executor=Executor(),
        generator=Generator(),
        citation_validator=Validator(),
        registry=build_default_agent_tool_registry(),
    ).run(
        AgentState(
            request_id="r1",
            thread_id="t1",
            original_query="q",
            current_query="q",
        )
    )

    assert result.state.termination_reason == "answer_completed"
    assert result.answer == "grounded answer"
    assert result.state.evidence_ids == ["e1"]
    assert result.state.evidence_sufficient is True
    assert any(step.kind == "tool" for step in result.trajectory)
