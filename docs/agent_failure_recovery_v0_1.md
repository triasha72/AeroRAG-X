# Phase 39 — Agent failure recovery and fault injection

Retry behavior is explicit and bounded by tool and failure class. Unknown
evidence and malformed responses are not silently retried into success.
Deterministic injected faults support regression testing.

A required dependency that remains unavailable after its bounded retry budget
terminates safely rather than allowing generation from absent evidence.
