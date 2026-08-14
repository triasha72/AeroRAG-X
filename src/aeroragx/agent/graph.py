"""Stateful tool-using LangGraph controller for AeroRAG-X."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, TypedDict, cast

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from aeroragx.agent.execution import (
    AgentCitationValidator,
    AgentGenerator,
    AgentToolExecutor,
    CitationValidationResult,
    GenerationResult,
)
from aeroragx.agent.planner import AgentPlanner, PlannerDecision
from aeroragx.agent.registry import AgentToolRegistry
from aeroragx.agent.routing import route_planner_decision
from aeroragx.agent.state import AgentState, AgentTerminationReason

AgentEventKind = Literal[
    "plan",
    "tool",
    "generate",
    "citation_validation",
    "terminate",
]


class AgentStepRecord(BaseModel):
    """One externally inspectable step in the agent trajectory."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sequence: int = Field(ge=1)
    kind: AgentEventKind
    detail: str = Field(min_length=1, max_length=500)


class AgentRunResult(BaseModel):
    """Terminal graph result with inspectable trajectory."""

    model_config = ConfigDict(extra="forbid")

    state: AgentState
    answer: str | None = None
    cited_evidence_ids: list[str] = Field(default_factory=list)
    citation_validation: CitationValidationResult | None = None
    trajectory: list[AgentStepRecord] = Field(default_factory=list)


class _GraphState(TypedDict):
    agent_state: AgentState
    planner_decision: PlannerDecision | None
    generation: GenerationResult | None
    citation_validation: CitationValidationResult | None
    trajectory: list[AgentStepRecord]


StateObserver = Callable[[AgentState], None]


class StatefulAgentGraph:
    """Compile and execute a bounded dynamic agent graph."""

    def __init__(
        self,
        *,
        planner: AgentPlanner,
        tool_executor: AgentToolExecutor,
        generator: AgentGenerator,
        citation_validator: AgentCitationValidator,
        registry: AgentToolRegistry,
    ) -> None:
        self._planner = planner
        self._tool_executor = tool_executor
        self._generator = generator
        self._citation_validator = citation_validator
        self._registry = registry

    def run(
        self,
        initial_state: AgentState,
        *,
        on_state_change: StateObserver | None = None,
    ) -> AgentRunResult:
        """Run until grounded completion, refusal, review, or budget termination."""

        graph = self._build_graph(on_state_change=on_state_change)
        final_state = cast(
            _GraphState,
            graph.compile().invoke(
                {
                    "agent_state": initial_state,
                    "planner_decision": None,
                    "generation": None,
                    "citation_validation": None,
                    "trajectory": [],
                },
                config={"recursion_limit": initial_state.maximum_steps * 6 + 20},
            ),
        )

        generation = final_state["generation"]
        validation = final_state["citation_validation"]

        return AgentRunResult(
            state=final_state["agent_state"],
            answer=None if generation is None else generation.answer,
            cited_evidence_ids=([] if generation is None else generation.cited_evidence_ids),
            citation_validation=validation,
            trajectory=final_state["trajectory"],
        )

    def _build_graph(
        self,
        *,
        on_state_change: StateObserver | None,
    ) -> StateGraph[_GraphState]:
        graph = StateGraph(_GraphState)

        def observe(state: AgentState) -> None:
            if on_state_change is not None:
                on_state_change(state)

        def event(
            state: _GraphState,
            *,
            kind: AgentEventKind,
            detail: str,
        ) -> list[AgentStepRecord]:
            return [
                *state["trajectory"],
                AgentStepRecord(
                    sequence=len(state["trajectory"]) + 1,
                    kind=kind,
                    detail=detail,
                ),
            ]

        def plan(state: _GraphState) -> dict[str, Any]:
            agent_state = state["agent_state"]
            if agent_state.step_number >= agent_state.maximum_steps:
                terminal = agent_state.terminate("step_budget_exhausted")
                observe(terminal)
                return {
                    "agent_state": terminal,
                    "planner_decision": None,
                    "trajectory": event(
                        state,
                        kind="terminate",
                        detail="Step budget exhausted before planning.",
                    ),
                }

            advanced = agent_state.advance_step()
            decision = self._planner.decide(advanced)
            observe(advanced)
            return {
                "agent_state": advanced,
                "planner_decision": decision,
                "trajectory": event(
                    state,
                    kind="plan",
                    detail=f"{decision.action}: {decision.reason}",
                ),
            }

        def plan_route(state: _GraphState) -> str:
            agent_state = state["agent_state"]
            if agent_state.termination_reason is not None:
                return "finish"

            decision = state["planner_decision"]
            if decision is None:
                return "finish"

            return route_planner_decision(agent_state, decision)

        def execute_tool(state: _GraphState) -> dict[str, Any]:
            agent_state = state["agent_state"]
            decision = state["planner_decision"]
            if decision is None or decision.selected_tool is None:
                raise RuntimeError("Tool execution requires a planner-selected tool.")

            definition = self._registry.get(decision.selected_tool)
            result = self._tool_executor.execute(
                decision.selected_tool,
                agent_state,
            )

            updated = agent_state.record_tool_call(
                result.call,
                retrieval_attempt=definition.counts_as_retrieval_attempt,
                evidence_ids=result.evidence_ids,
                document_ids=result.document_ids,
            )

            payload = updated.model_dump(mode="python")
            if result.call.tool_name == "hybrid_retrieve":
                # New evidence must be reassessed even if an earlier retrieval
                # attempt was insufficient.
                payload["evidence_sufficient"] = None
                updated = AgentState.model_validate(payload)
            elif result.evidence_sufficient is not None:
                payload["evidence_sufficient"] = result.evidence_sufficient
                updated = AgentState.model_validate(payload)

            observe(updated)
            return {
                "agent_state": updated,
                "trajectory": event(
                    state,
                    kind="tool",
                    detail=(
                        f"{result.call.tool_name}:{result.call.status}:{result.call.tool_call_id}"
                    ),
                ),
            }

        def generate(state: _GraphState) -> dict[str, Any]:
            generation = self._generator.generate(state["agent_state"])
            return {
                "generation": generation,
                "trajectory": event(
                    state,
                    kind="generate",
                    detail="Generated one candidate grounded answer.",
                ),
            }

        def validate_citations(state: _GraphState) -> dict[str, Any]:
            generation = state["generation"]
            if generation is None:
                raise RuntimeError("Citation validation requires a generation result.")

            validation = self._citation_validator.validate(
                generation,
                state["agent_state"],
            )
            return {
                "citation_validation": validation,
                "trajectory": event(
                    state,
                    kind="citation_validation",
                    detail=f"citation_valid={validation.valid}",
                ),
            }

        def validation_route(state: _GraphState) -> str:
            validation = state["citation_validation"]
            if validation is None:
                return "citation_failure"
            return "complete" if validation.valid else "citation_failure"

        def terminal_update(
            state: _GraphState,
            reason: AgentTerminationReason,
        ) -> dict[str, Any]:
            """Return one validated terminal graph-state update."""

            agent_state = state["agent_state"]
            terminal = agent_state.terminate(reason)
            observe(terminal)

            return {
                "agent_state": terminal,
                "trajectory": event(
                    state,
                    kind="terminate",
                    detail=reason,
                ),
            }

        def complete(state: _GraphState) -> dict[str, Any]:
            """Terminate after a grounded answer passes validation."""

            return terminal_update(
                state,
                "answer_completed",
            )

        def grounded_refusal(
            state: _GraphState,
        ) -> dict[str, Any]:
            """Terminate with a grounded refusal."""

            return terminal_update(
                state,
                "grounded_refusal",
            )

        def human_review(
            state: _GraphState,
        ) -> dict[str, Any]:
            """Terminate at the explicit human-review boundary."""

            return terminal_update(
                state,
                "human_review_required",
            )

        def step_budget_exhausted(
            state: _GraphState,
        ) -> dict[str, Any]:
            """Terminate after exhausting the graph-step budget."""

            return terminal_update(
                state,
                "step_budget_exhausted",
            )

        def tool_budget_exhausted(
            state: _GraphState,
        ) -> dict[str, Any]:
            """Terminate after exhausting the tool-call budget."""

            return terminal_update(
                state,
                "tool_budget_exhausted",
            )

        def citation_failure(
            state: _GraphState,
        ) -> dict[str, Any]:
            """Terminate when candidate citations fail validation."""

            return terminal_update(
                state,
                "citation_validation_failure",
            )

        graph.add_node("plan", plan)
        graph.add_node("execute_tool", execute_tool)
        graph.add_node("generate", generate)
        graph.add_node(
            "validate_citations",
            validate_citations,
        )

        graph.add_node(
            "complete",
            complete,
            input_schema=_GraphState,
        )

        graph.add_node(
            "grounded_refusal",
            grounded_refusal,
            input_schema=_GraphState,
        )

        graph.add_node(
            "human_review",
            human_review,
            input_schema=_GraphState,
        )

        graph.add_node(
            "step_budget_exhausted",
            step_budget_exhausted,
            input_schema=_GraphState,
        )

        graph.add_node(
            "tool_budget_exhausted",
            tool_budget_exhausted,
            input_schema=_GraphState,
        )

        graph.add_node(
            "citation_failure",
            citation_failure,
            input_schema=_GraphState,
        )

        graph.add_edge(START, "plan")
        graph.add_conditional_edges(
            "plan",
            plan_route,
            {
                "execute_tool": "execute_tool",
                "generate": "generate",
                "grounded_refusal": "grounded_refusal",
                "human_review": "human_review",
                "tool_budget_exhausted": "tool_budget_exhausted",
                "finish": END,
            },
        )
        graph.add_edge("execute_tool", "plan")
        graph.add_edge("generate", "validate_citations")
        graph.add_conditional_edges(
            "validate_citations",
            validation_route,
            {
                "complete": "complete",
                "citation_failure": "citation_failure",
            },
        )
        graph.add_edge("complete", END)
        graph.add_edge("grounded_refusal", END)
        graph.add_edge("human_review", END)
        graph.add_edge("step_budget_exhausted", END)
        graph.add_edge("tool_budget_exhausted", END)
        graph.add_edge("citation_failure", END)

        return graph
