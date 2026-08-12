# Agentic retrieval observability v0.1

## Purpose

AeroRAG-X records the adaptive-retrieval controller that produced each adaptive grounded answer. This makes native and LangGraph executions distinguishable in serialized answer metadata while preserving the same bounded retrieval policy and evidence-provenance requirements.

## Answer metadata contract

When retrieval metadata is enabled, an adaptive grounded answer includes one of these values:

```json
{
  "adaptive_retrieval_orchestrator": "native"
}