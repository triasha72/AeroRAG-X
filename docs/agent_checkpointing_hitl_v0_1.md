# Phase 38 — Checkpointing and human-in-the-loop

Every observed validated `AgentState` may now be persisted as an immutable,
versioned checkpoint. A development JSON store enables deterministic local
recovery without requiring an external service.

Human review is represented by explicit request/response contracts. Approve,
reject, and edit decisions preserve the original paused state and produce a new
validated resume state.

The file-backed store is intentionally a development persistence layer. The
distributed service phases can replace it with PostgreSQL-backed persistence
without changing the review semantics.
