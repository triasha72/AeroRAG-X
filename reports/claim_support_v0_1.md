# Claim-evidence support evaluation v0.1

## Scope

This evaluation measures whether each formal grounded claim is supported by the evidence cited by that claim.

The 85-claim benchmark contains 32 Base + RAG claims and 53 LoRA + RAG claims from the frozen grounded recapture.

Ten exact-containment cases were accepted automatically. The remaining 75 were adjudicated under the frozen claim-support policy.

This is a single structured adjudication pass, not an independent multi-assessor human annotation study.

## Results

| System | Claims | Supported | Partial | Unsupported | Contradicted | Strict support | Support-or-partial |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base + RAG | 32 | 21 | 7 | 4 | 0 | 0.6562 | 0.8750 |
| LoRA + RAG | 53 | 36 | 12 | 2 | 3 | 0.6792 | 0.9057 |

## Comparison

LoRA - Base strict-support-rate difference: +0.0230

LoRA - Base support-or-partial-rate difference: +0.0307

## Interpretation guardrails

- These metrics evaluate claim-to-cited-evidence support, not universal factual correctness.
- `PARTIALLY_SUPPORTED` remains distinct from fully supported claims.
- `CONTRADICTED` is reserved for material conflict with the cited evidence.
- Higher claim count is not treated as higher quality by itself.
- No generation, retrieval, or training run was repeated for this adjudication stage.
