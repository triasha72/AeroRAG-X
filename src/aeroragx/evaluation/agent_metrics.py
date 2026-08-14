"""Deterministic metrics for frozen agent-trajectory evaluation."""

from __future__ import annotations

from statistics import median

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.evaluation.agent_trajectory import AgentTrajectoryObservation


class AgentTrajectoryMetrics(BaseModel):
    """Aggregate behavioral, recovery, and efficiency metrics."""

    model_config = ConfigDict(extra="forbid")

    case_count: int = Field(ge=1)
    task_completion_rate: float = Field(ge=0.0, le=1.0)
    termination_accuracy: float = Field(ge=0.0, le=1.0)
    tool_selection_accuracy: float = Field(ge=0.0, le=1.0)
    required_tool_recall: float = Field(ge=0.0, le=1.0)
    forbidden_tool_avoidance: float = Field(ge=0.0, le=1.0)
    tool_budget_compliance: float = Field(ge=0.0, le=1.0)
    safe_refusal_accuracy: float = Field(ge=0.0, le=1.0)
    retry_case_rate: float = Field(ge=0.0, le=1.0)
    recovery_success_rate: float = Field(ge=0.0, le=1.0)
    human_review_trigger_rate: float = Field(ge=0.0, le=1.0)
    mean_tool_calls: float = Field(ge=0.0)
    mean_latency_ms: float = Field(ge=0.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)


def evaluate_agent_trajectories(
    observations: list[AgentTrajectoryObservation],
) -> AgentTrajectoryMetrics:
    if not observations:
        raise ValueError("Agent trajectory evaluation requires at least one observation.")

    termination_hits = 0
    completion_hits = 0
    selection_hits = 0
    required_hits = 0
    required_total = 0
    forbidden_clean = 0
    budget_hits = 0
    refusal_hits = 0
    refusal_total = 0
    retry_cases = 0
    recovery_attempt_cases = 0
    recovery_successes = 0
    human_review_cases = 0
    tool_calls: list[int] = []
    latencies: list[float] = []

    for observation in observations:
        case = observation.case
        run = observation.run
        used_tools = [call.tool_name for call in run.state.tool_history]
        used_tool_set = set(used_tools)
        required_set = set(case.required_tools)
        forbidden_set = set(case.forbidden_tools)

        terminal_matches = run.state.termination_reason == case.expected_termination
        termination_hits += int(terminal_matches)

        if case.answerable:
            completion_hits += int(
                run.state.termination_reason == "answer_completed"
                and run.answer is not None
            )
        else:
            completion_hits += int(
                run.state.termination_reason
                in {
                    "grounded_refusal",
                    "insufficient_evidence",
                    "unrecoverable_tool_failure",
                    "citation_validation_failure",
                    "human_review_required",
                }
            )

        selection_hits += int(
            required_set.issubset(used_tool_set)
            and not (forbidden_set & used_tool_set)
        )
        required_total += len(required_set)
        required_hits += sum(tool in used_tool_set for tool in required_set)
        forbidden_clean += int(not (forbidden_set & used_tool_set))
        budget_hits += int(run.state.tool_call_count <= case.maximum_tool_calls)

        if not case.answerable:
            refusal_total += 1
            refusal_hits += int(
                run.state.termination_reason
                in {
                    "grounded_refusal",
                    "insufficient_evidence",
                    "unrecoverable_tool_failure",
                    "citation_validation_failure",
                }
            )

        if observation.retry_count > 0:
            retry_cases += 1
            recovery_attempt_cases += 1
            recovery_successes += int(observation.recovered_after_failure)

        human_review_cases += int(observation.human_review_triggered)
        tool_calls.append(run.state.tool_call_count)
        latencies.append(observation.latency_ms)

    ordered = sorted(latencies)
    p95_index = max(int(round(0.95 * (len(ordered) - 1))), 0)

    return AgentTrajectoryMetrics(
        case_count=len(observations),
        task_completion_rate=completion_hits / len(observations),
        termination_accuracy=termination_hits / len(observations),
        tool_selection_accuracy=selection_hits / len(observations),
        required_tool_recall=(
            1.0 if required_total == 0 else required_hits / required_total
        ),
        forbidden_tool_avoidance=forbidden_clean / len(observations),
        tool_budget_compliance=budget_hits / len(observations),
        safe_refusal_accuracy=(
            1.0 if refusal_total == 0 else refusal_hits / refusal_total
        ),
        retry_case_rate=retry_cases / len(observations),
        recovery_success_rate=(
            1.0
            if recovery_attempt_cases == 0
            else recovery_successes / recovery_attempt_cases
        ),
        human_review_trigger_rate=human_review_cases / len(observations),
        mean_tool_calls=sum(tool_calls) / len(tool_calls),
        mean_latency_ms=sum(latencies) / len(latencies),
        p50_latency_ms=float(median(latencies)),
        p95_latency_ms=ordered[p95_index],
    )
