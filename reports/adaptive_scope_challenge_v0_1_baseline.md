# Phase 27 unsupported-scope development baseline v0.1

## Scope

This is a development-only evaluation of the unchanged Phase 25 bounded adaptive-retrieval policy. It does not reuse or modify the protected Phase 26 held-out benchmark.

## Results

| Metric | Single pass | Bounded adaptive |
|---|---:|---:|
| Answerability accuracy | 78.57% | 78.57% |
| Unsupported refusal | 70.00% | 70.00% |

## Adaptive behavior

- Recovery triggers: 7
- Successful recoveries: 0
- Recovery grounded refusals: 7
- Unsupported queries answered after adaptive retrieval: 3 of 10

## Interpretation

This baseline records current behavior before any scope-protection policy is designed or enabled.
