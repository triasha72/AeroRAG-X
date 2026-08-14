# Phase 41 — Microservice contracts

This phase defines the network boundary before running separate processes.
Agent, retrieval, and inference requests preserve `request_id`, `trace_id`, and
`thread_id`. Evidence retains evidence/document IDs and citation provenance.

The async clients use typed Pydantic request/response contracts. Actual
containerized service processes are Phase 42.
