# Bounded adaptive retrieval

Phase 25 adds one deterministic evidence-recovery path to AeroRAG-X.

## Contract

```text
QUESTION
   ↓
RETRIEVE (attempt 1)
   ↓
ASSESS
   ├── sufficient   → GENERATE
   └── insufficient → REWRITE QUERY
                         ↓
                    RETRIEVE (attempt 2)
                         ↓
                       ASSESS
                         ├── sufficient   → GENERATE
                         └── insufficient → GROUNDED REFUSAL
```

The controller permits at most two retrieval passes and one query rewrite.
There is no recursive retry, autonomous planning loop, or model-generated
rewrite.

## Deterministic rewrite

The recovery rewrite preserves the original question and appends fixed
corpus-retrieval context from `configs/adaptive_retrieval_v0_1.yaml`.

```text
original question + "NASA aerospace technical report"
```

The original question remains the query evaluated by the evidence-sufficiency
gate and passed to the generation provider. The rewritten string is used only
for the second retrieval pass.

## Provenance and refusals

When enabled, `retrieval_metadata.adaptive_retrieval` retains:

- both retrieval queries;
- the exact state sequence;
- every retrieved chunk's citation, page, document hash, rank, and retrieval
  source provenance;
- evidence-sufficiency decisions and reasons for each attempt;
- the retrieval terminal state.

If the second assessment remains insufficient, AeroRAG-X returns the existing
grounded-refusal response and bypasses the generation provider.

## Enable the policy

The policy is opt-in to preserve the frozen Phase 24 and held-out v0.4
single-pass behavior.

```bash
aeroragx ntrs-grounded-answer \
  --query "How can battery thermal runaway propagate in electric aircraft?" \
  --adaptive-retrieval-config configs/adaptive_retrieval_v0_1.yaml
```

For the API, set this explicit environment flag before starting the service:

```bash
export AERORAGX_ENABLE_ADAPTIVE_RETRIEVAL=true
uvicorn aeroragx.api.app:app
```

## Protected baseline

`artifacts/evaluation/phase25_baseline_manifest_v0_1.json` pins the Phase 24
summary, quality checksums, report, held-out v0.4 artifact, and relevant
single-pass configurations. Phase 25 must not modify those inputs in response
to an evaluation outcome.

## Phase 26 boundary

Phase 25 implements the controller and parity tests. The comparison of
single-pass and adaptive retrieval, including recovery quality, latency,
retrieval overhead, citation validity, and unsupported-query behavior, belongs
to Phase 26.
