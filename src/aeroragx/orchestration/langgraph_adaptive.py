"""LangGraph implementation of AeroRAG-X's bounded adaptive retrieval policy."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from aeroragx.generation.adaptive_retrieval import (
    AdaptiveEvidenceAssessment,
    AdaptiveEvidenceProvenance,
    AdaptiveRetrievalAttempt,
    AdaptiveRetrievalConfig,
    AdaptiveRetrievalState,
    AdaptiveRetrievalTrace,
    BoundedRetrievalOutcome,
    DeterministicQueryRewriter,
    QueryRewriter,
)

type GraphRoute = Literal["generate", "rewrite_query", "grounded_refusal"]
type TerminalState = Literal["generate", "grounded_refusal"]


class _LangGraphAdaptiveState(TypedDict):
    """Internal graph state for one bounded retrieval request."""

    original_query: str
    current_query: str
    active_hit_set: Any | None
    hit_sets: list[Any]
    evidence: list[Any]
    assessment: AdaptiveEvidenceAssessment | None
    attempts: list[AdaptiveRetrievalAttempt]
    rewritten_query: str | None
    terminal_state: TerminalState | None


@dataclass(frozen=True, slots=True)
class LangGraphBoundedAdaptiveRetrievalController[HitT, EvidenceT]:
    """Execute the existing deterministic recovery policy with LangGraph."""

    config: AdaptiveRetrievalConfig
    rewriter: QueryRewriter | None = None

    def execute(
        self,
        *,
        original_query: str,
        retrieve: Callable[[str], HitT],
        build_evidence: Callable[[HitT], Sequence[EvidenceT]],
        assess_evidence: Callable[[Sequence[EvidenceT]], AdaptiveEvidenceAssessment],
        build_provenance: Callable[[HitT, int], Sequence[AdaptiveEvidenceProvenance]],
        returned_evidence_count: Callable[[HitT], int],
    ) -> BoundedRetrievalOutcome[HitT, EvidenceT]:
        """Run a compiled LangGraph with the same bounded policy as native retrieval."""

        normalized_query = original_query.strip()
        if not normalized_query:
            raise ValueError("original_query must not be blank.")

        rewriter = (
            DeterministicQueryRewriter(self.config) if self.rewriter is None else self.rewriter
        )

        def retrieve_initial(
            state: _LangGraphAdaptiveState,
        ) -> dict[str, Any]:
            hit_set = retrieve(state["original_query"])
            return {
                "active_hit_set": hit_set,
                "hit_sets": [hit_set],
                "current_query": state["original_query"],
            }

        def assess_initial(
            state: _LangGraphAdaptiveState,
        ) -> dict[str, Any]:
            hit_set = cast(HitT, state["active_hit_set"])
            evidence = list(build_evidence(hit_set))
            assessment = assess_evidence(evidence)
            attempt = build_attempt(
                attempt_number=1,
                retrieval_query=state["original_query"],
                hit_set=hit_set,
                evidence=evidence,
                assessment=assessment,
                build_provenance=build_provenance,
                returned_evidence_count=returned_evidence_count,
            )
            return {
                "evidence": evidence,
                "assessment": assessment,
                "attempts": [attempt],
            }

        def route_initial(state: _LangGraphAdaptiveState) -> GraphRoute:
            assessment = require_assessment(state)
            if assessment.sufficient:
                return "generate"
            if self.config.maximum_retrieval_passes == 1:
                return "grounded_refusal"
            return "rewrite_query"

        def rewrite_query(
            state: _LangGraphAdaptiveState,
        ) -> dict[str, Any]:
            assessment = require_assessment(state)
            rewritten_query = rewriter.rewrite(
                original_query=state["original_query"],
                assessment=assessment,
            ).strip()

            if not rewritten_query:
                raise ValueError("Deterministic recovery rewrite must not be blank.")

            if rewritten_query.casefold() == state["original_query"].casefold():
                raise ValueError("Deterministic recovery rewrite must change the retrieval query.")

            return {
                "current_query": rewritten_query,
                "rewritten_query": rewritten_query,
            }

        def retrieve_recovery(
            state: _LangGraphAdaptiveState,
        ) -> dict[str, Any]:
            hit_set = retrieve(state["current_query"])
            return {
                "active_hit_set": hit_set,
                "hit_sets": [*state["hit_sets"], hit_set],
            }

        def assess_recovery(
            state: _LangGraphAdaptiveState,
        ) -> dict[str, Any]:
            hit_set = cast(HitT, state["active_hit_set"])
            evidence = list(build_evidence(hit_set))
            assessment = assess_evidence(evidence)
            attempt = build_attempt(
                attempt_number=2,
                retrieval_query=state["current_query"],
                hit_set=hit_set,
                evidence=evidence,
                assessment=assessment,
                build_provenance=build_provenance,
                returned_evidence_count=returned_evidence_count,
            )
            return {
                "evidence": evidence,
                "assessment": assessment,
                "attempts": [*state["attempts"], attempt],
            }

        def route_recovery(state: _LangGraphAdaptiveState) -> GraphRoute:
            if require_assessment(state).sufficient:
                return "generate"
            return "grounded_refusal"

        def generate(
            state: _LangGraphAdaptiveState,
        ) -> dict[str, Any]:
            del state
            return {"terminal_state": "generate"}

        def grounded_refusal(
            state: _LangGraphAdaptiveState,
        ) -> dict[str, Any]:
            del state
            return {"terminal_state": "grounded_refusal"}

        graph = StateGraph(_LangGraphAdaptiveState)
        graph.add_node("retrieve_initial", retrieve_initial)
        graph.add_node("assess_initial", assess_initial)
        graph.add_node("rewrite_query", rewrite_query)
        graph.add_node("retrieve_recovery", retrieve_recovery)
        graph.add_node("assess_recovery", assess_recovery)
        graph.add_node("generate", generate)
        graph.add_node("grounded_refusal", grounded_refusal)

        graph.add_edge(START, "retrieve_initial")
        graph.add_edge("retrieve_initial", "assess_initial")
        graph.add_conditional_edges(
            "assess_initial",
            route_initial,
            {
                "generate": "generate",
                "rewrite_query": "rewrite_query",
                "grounded_refusal": "grounded_refusal",
            },
        )
        graph.add_edge("rewrite_query", "retrieve_recovery")
        graph.add_edge("retrieve_recovery", "assess_recovery")
        graph.add_conditional_edges(
            "assess_recovery",
            route_recovery,
            {
                "generate": "generate",
                "grounded_refusal": "grounded_refusal",
            },
        )
        graph.add_edge("generate", END)
        graph.add_edge("grounded_refusal", END)

        final_state = cast(
            _LangGraphAdaptiveState,
            graph.compile().invoke(
                {
                    "original_query": normalized_query,
                    "current_query": normalized_query,
                    "active_hit_set": None,
                    "hit_sets": [],
                    "evidence": [],
                    "assessment": None,
                    "attempts": [],
                    "rewritten_query": None,
                    "terminal_state": None,
                }
            ),
        )

        assessment = require_assessment(final_state)
        terminal_state = final_state["terminal_state"]
        if terminal_state is None:
            raise RuntimeError("LangGraph completed without a terminal state.")

        hit_sets = [cast(HitT, hit_set) for hit_set in final_state["hit_sets"]]
        evidence = [cast(EvidenceT, item) for item in final_state["evidence"]]

        return BoundedRetrievalOutcome(
            hit_sets=hit_sets,
            evidence=evidence,
            assessment=assessment,
            trace=build_trace(
                original_query=normalized_query,
                rewritten_query=final_state["rewritten_query"],
                attempts=final_state["attempts"],
                retrieval_terminal_state=terminal_state,
            ),
        )


def require_assessment(
    state: _LangGraphAdaptiveState,
) -> AdaptiveEvidenceAssessment:
    """Return the current assessment or reject an invalid graph state."""

    assessment = state["assessment"]
    if assessment is None:
        raise RuntimeError("LangGraph routing requires an evidence assessment.")
    return assessment


def build_attempt[HitT, EvidenceT](
    *,
    attempt_number: int,
    retrieval_query: str,
    hit_set: HitT,
    evidence: Sequence[EvidenceT],
    assessment: AdaptiveEvidenceAssessment,
    build_provenance: Callable[[HitT, int], Sequence[AdaptiveEvidenceProvenance]],
    returned_evidence_count: Callable[[HitT], int],
) -> AdaptiveRetrievalAttempt:
    """Create one validated retrieval-attempt record."""

    return AdaptiveRetrievalAttempt(
        attempt_number=attempt_number,
        retrieval_query=retrieval_query,
        returned_evidence_count=returned_evidence_count(hit_set),
        used_evidence_count=len(evidence),
        assessment=assessment,
        evidence_provenance=list(build_provenance(hit_set, attempt_number)),
    )


def build_trace(
    *,
    original_query: str,
    rewritten_query: str | None,
    attempts: list[AdaptiveRetrievalAttempt],
    retrieval_terminal_state: TerminalState,
) -> AdaptiveRetrievalTrace:
    """Create the same validated trace shape as the native controller."""

    terminal_state = (
        AdaptiveRetrievalState.GENERATE
        if retrieval_terminal_state == "generate"
        else AdaptiveRetrievalState.GROUNDED_REFUSAL
    )

    states = (
        [
            AdaptiveRetrievalState.RETRIEVE_INITIAL,
            AdaptiveRetrievalState.ASSESS_INITIAL,
            terminal_state,
        ]
        if len(attempts) == 1
        else [
            AdaptiveRetrievalState.RETRIEVE_INITIAL,
            AdaptiveRetrievalState.ASSESS_INITIAL,
            AdaptiveRetrievalState.REWRITE_QUERY,
            AdaptiveRetrievalState.RETRIEVE_RECOVERY,
            AdaptiveRetrievalState.ASSESS_RECOVERY,
            terminal_state,
        ]
    )

    return AdaptiveRetrievalTrace(
        original_query=original_query,
        rewritten_query=rewritten_query,
        states=states,
        attempts=attempts,
        retrieval_terminal_state=retrieval_terminal_state,
    )
