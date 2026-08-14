# Phase 37 — Stateful tool-using agent graph

Phase 37 composes the bounded Phase 36 tools into a dynamically routed
LangGraph state machine.

The planner is injectable and may be deterministic or model-backed, but every
decision is validated against a closed action schema and an explicit tool
registry. The graph never exposes arbitrary Python execution.

Terminal reasons are explicit, including grounded refusal, citation failure,
human-review interruption, and step/tool budget exhaustion.

This phase establishes dynamic routing and inspectable trajectories. Persistence
and human-review resumption are Phase 38.
