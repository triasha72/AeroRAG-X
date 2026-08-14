# Phase 36 — Bounded agent tool contracts v0.1

## Objective

Phase 36 creates the typed, provenance-preserving tool boundary required before
AeroRAG-X is allowed to become a stateful tool-using agent.

The existing LangGraph adaptive controller remains a bounded deterministic
retrieval workflow. Phase 36 does not replace it and does not yet claim
autonomous planning.

## Allowed tools

The Phase 36 registry contains exactly:

```text
hybrid_retrieve
fetch_source_context
check_evidence_sufficiency
validate_citations
compare_sources
```

The future graph may select only registered tools.

## State budgets

`AgentState` records explicit limits for:

```text
maximum_steps
maximum_tool_calls
maximum_retrieval_attempts
```

State also preserves:

```text
request_id
thread_id
original_query
current_query
selected_tool
tool_history
evidence_ids
document_ids
evidence_sufficient
previous_failures
human_review_required
termination_reason
```

This phase establishes contracts only. Dynamic LangGraph routing is Phase 37.

## Reliability boundary

Backend exceptions are converted to structured tool-call failures. Tool wrappers
do not silently promote backend failures into successful results.

Citation validation is deterministic and rejects unknown or duplicated evidence
identifiers.

Source-context lookup rejects backend data for evidence IDs that were not
requested.

## Evaluation boundary

Phase 36 tests contract invariants, state budgets, provenance preservation,
structured backend failure handling, registry restrictions, and deterministic
citation validation.

Agent trajectory quality is not claimed until the later frozen trajectory
benchmark.
