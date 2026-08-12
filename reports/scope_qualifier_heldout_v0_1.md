# Phase 28 scope-qualifier held-out evaluation v0.1

## Scope

This evaluation compares the existing v0.2.1 sufficiency policy with the opt-in v0.3.0 scope-qualifier safeguard on a separately authored, frozen held-out benchmark.

Phase 26 protected held-out data was not used or modified. Phase 27 development questions were not reused.

## Results

| Policy | Mode | Answerability accuracy | Unsupported refusal |
|---|---|---:|---:|
| Baseline v0.2.1 | Single pass | 50.00% | 40.00% |
| Baseline v0.2.1 | Bounded adaptive | 50.00% | 40.00% |
| Scope guard v0.3.0 | Single pass | 92.86% | 100.00% |
| Scope guard v0.3.0 | Bounded adaptive | 92.86% | 100.00% |

## Safety diagnostics

- Baseline bounded-adaptive false refusals: 1
- Scope-guard bounded-adaptive false refusals: 1
- Baseline bounded-adaptive unsupported answers: 6
- Scope-guard bounded-adaptive unsupported answers: 0
- Scope-guard adaptive recovery triggers: 11

## Decision rule

The v0.3.0 safeguard is acceptable on this held-out benchmark only if it improves or preserves unsupported-query refusal without reducing answerability accuracy or increasing false refusals. Regardless of this result, it remains opt-in until a later policy decision is separately reviewed.
