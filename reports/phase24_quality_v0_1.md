# Phase 24 consolidated quality evaluation v0.1

## Scope

This report consolidates the frozen Phase 24 quality evaluations without rerunning generation, retrieval, training, or model selection.

The component evaluations measure different properties:

- semantic expected-concept coverage;
- claim-to-cited-evidence support;
- answer-to-formal-claim completeness;
- within-answer claim redundancy/overlap;
- unsupported-query response behavior.

They are intentionally reported separately rather than collapsed into a single score.

## Grounded-system comparison

| Dimension | Base + RAG | LoRA + RAG | LoRA - Base |
|---|---:|---:|---:|
| Semantic concept coverage, conservative micro | 38.16% | 51.32% | +13.16 pp |
| Semantic concept coverage, upper-bound micro | 53.95% | 65.79% | +11.84 pp |
| Strict claim-evidence support | 65.62% | 67.92% | +2.30 pp |
| Support-or-partial claim-evidence support | 87.50% | 90.57% | +3.07 pp |
| Full answer-to-claim capture | 10.00% | 45.00% | +35.00 pp |
| Full-or-partial answer-to-claim capture | 60.00% | 95.00% | +35.00 pp |
| Full redundancy rate | 0.00% | 1.89% | +1.89 pp |
| Partial-overlap rate | 12.50% | 39.62% | +27.12 pp |
| Unsupported-query safe non-assertion | 100.00% | 100.00% | +0.00 pp |

## Claim decomposition

- Base + RAG produced **32** formal claims.
- LoRA + RAG produced **53** formal claims.
- Base + RAG had **0** contradicted claim(s) under the frozen claim-support policy.
- LoRA + RAG had **3** contradicted claim(s) under the frozen claim-support policy.
- The LoRA condition therefore shows richer formal decomposition, but the higher claim count is not treated as a quality metric by itself.

## Unsupported-query behavior

| Condition | Safe non-assertion | Unsupported-assertion rate |
|---|---:|---:|
| Base closed-book | 58.33% | 41.67% |
| LoRA closed-book | 75.00% | 25.00% |
| Base + RAG | 100.00% | 0.00% |
| LoRA + RAG | 100.00% | 0.00% |

## Findings

1. **Semantic coverage:** LoRA + RAG contains more of the predefined technical concepts than Base + RAG on the protected answerable benchmark.
2. **Evidence support:** claim-to-cited-evidence support rates remain broadly similar between the two grounded conditions; the LoRA condition also contains a small number of contradicted claims.
3. **Formal completeness:** LoRA + RAG captures materially more of its prose-answer content in the formal claim structure.
4. **Redundancy:** the additional LoRA claims are rarely fully redundant, but partial semantic overlap is substantially higher.
5. **Unsupported-query boundary:** both grounded conditions avoid unsupported substantive answering on all 12 protected unsupported queries, while the closed-book conditions do not.

## Defensible conclusion

On this protected grounded benchmark, LoRA increased structured technical decomposition and answer-to-claim completeness, and it produced higher expected-concept coverage while maintaining broadly similar claim-to-evidence support rates. The additional claims were rarely fully redundant, although partial semantic overlap increased substantially and a small number of contradicted LoRA claims remained. Retrieval-grounded execution provided the strongest unsupported-query boundary in both grounded conditions.

## Guardrails

- These results do not establish universal factual accuracy or universal model superiority.
- Claim-evidence support, semantic coverage, completeness, redundancy, and unsupported-query behavior are separate properties.
- `OVERLAPPING` does not mean fully redundant.
- `UNSUPPORTED_ASSERTION` is defined relative to the frozen benchmark contract.
- Adjudication results come from single structured passes under frozen policies, not independent multi-assessor studies.
- No model, retrieval, training, or generation rerun was performed for this consolidation.
