# Within-answer claim redundancy evaluation v0.1

## Scope

This evaluation measures semantic redundancy among formal claims generated within the same grounded answer.

The benchmark contains 85 frozen formal claims: 32 Base + RAG and 53 LoRA + RAG.

Sixteen singleton-answer claims were deterministically classified as DISTINCT. The remaining 69 claims were adjudicated under the frozen redundancy policy.

This is a single structured adjudication pass under a frozen policy, not an independent multi-assessor human annotation study.

## Results

| System | Claims | Distinct | Overlapping | Redundant | Redundancy rate | Overlap rate | Nonredundant rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base + RAG | 32 | 28 | 4 | 0 | 0.0000 | 0.1250 | 1.0000 |
| LoRA + RAG | 53 | 31 | 21 | 1 | 0.0189 | 0.3962 | 0.9811 |

## Comparison

LoRA - Base redundancy-rate difference: +0.0189

LoRA - Base overlap-rate difference: +0.2712

LoRA - Base nonredundant-rate difference: -0.0189

## Interpretation guardrails

- `OVERLAPPING` claims share material content but still contribute additional information.
- `REDUNDANT` is reserved for claims whose material content is already fully captured by sibling claims.
- Low redundancy does not imply factual correctness or evidence support.
- Higher raw claim count is not treated as higher quality by itself.
- No generation, retrieval, or training run was repeated for this adjudication stage.
