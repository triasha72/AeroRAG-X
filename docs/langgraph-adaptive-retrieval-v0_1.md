# LangGraph bounded adaptive retrieval v0.1

## Purpose

This implementation provides an opt-in LangGraph execution path for AeroRAG-X's existing bounded adaptive-retrieval policy. It preserves the Phase 25 retrieval limits, deterministic query rewrite behavior, evidence provenance, and grounded-refusal behavior.

The native controller remains the default. LangGraph is selected only when explicitly requested.

## Workflow

```text
START
  |
  v
retrieve_initial
  |
  v
assess_initial
  |---------------- sufficient ----------------> generate ---> END
  |
  |--- insufficient and rewrite available ---> rewrite_query
                                                |
                                                v
                                         retrieve_recovery
                                                |
                                                v
                                         assess_recovery
                                                |--------- sufficient --------> generate ---> END
                                                |
                                                |--- insufficient -----------> grounded_refusal ---> END
```

The workflow has deterministic terminal paths:

- At most two retrieval passes.
- At most one deterministic query rewrite.
- A sufficient evidence assessment proceeds to generation.
- An insufficient final assessment returns a provenance-preserving grounded refusal.

## Installation

Install the optional agentic dependencies:

```bash
python -m pip install -e ".[agentic]"
```

## Runtime selection

`native` is the default and preserves the pre-LangGraph implementation:

```python
RuntimeConfig(
    adaptive_retrieval_config=Path("configs/adaptive_retrieval_v0_1.yaml"),
    adaptive_retrieval_orchestrator="native",
)
```

Select LangGraph explicitly:

```python
RuntimeConfig(
    adaptive_retrieval_config=Path("configs/adaptive_retrieval_v0_1.yaml"),
    adaptive_retrieval_orchestrator="langgraph",
)
```

## CLI selection

```bash
aeroragx ntrs-grounded-answer \
  --query "What evidence supports thermal protection for re-entry vehicles?" \
  --adaptive-retrieval-config configs/adaptive_retrieval_v0_1.yaml \
  --adaptive-retrieval-orchestrator langgraph
```

## API selection

```bash
export AERORAGX_ENABLE_ADAPTIVE_RETRIEVAL=true
export AERORAGX_ADAPTIVE_RETRIEVAL_ORCHESTRATOR=langgraph
```

Allowed values for `AERORAGX_ADAPTIVE_RETRIEVAL_ORCHESTRATOR` are:

- `native`
- `langgraph`

Unknown values fail during API settings validation.

## Validation

The implementation is covered by:

- Parity tests for sufficient initial retrieval, successful recovery, and grounded refusal.
- Runtime-selection tests for native default behavior and explicit LangGraph opt-in.
- API environment-variable validation tests.
- Repository-wide formatting, linting, type checking, and regression tests.
- A local CLI smoke test using the `langgraph` controller.

## Evaluation boundaries

This work does not alter protected Phase 26 evaluation data or Phase 28 held-out data. The LangGraph path reuses the existing bounded policy rather than tuning thresholds from protected or held-out results.
