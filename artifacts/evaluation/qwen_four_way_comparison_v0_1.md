# Qwen Four-Way System Study — v0.1

## Conditions

The study compares four conditions:

1. Base Qwen closed-book
2. LoRA-adapted Qwen closed-book
3. Base Qwen with the full grounded-RAG system
4. LoRA-adapted Qwen with the full grounded-RAG system

The grounded-RAG conditions include retrieval, reranking, evidence-sufficiency gating, grounded generation, and citation validation.

The study should therefore be interpreted as a system ablation rather than a pure retrieval-only ablation.

## Aggregate results

| Metric | Base closed-book | LoRA closed-book | Base + grounded RAG | LoRA + grounded RAG |
|---|---:|---:|---:|---:|
| Completed | 27/32 | 32/32 | 32/32 | 32/32 |
| Generation failures | 5 | 0 | 0 | 0 |
| Answerability accuracy | 0.6250 | 0.7812 | 1.0000 | 1.0000 |
| Valid unsupported refusal | 0.0000 | 0.4167 | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 | 0.9310 | 0.9310 |
| Structural validity | 0.8438 | 1.0000 | 1.0000 | 1.0000 |
| Answerable formal claims | 21 | 33 | 32 | 53 |
| Claims / answerable query | 1.050 | 1.650 | 1.600 | 2.650 |

## Adapter effect without grounded RAG

LoRA improved closed-book structured-generation reliability:

- completed queries increased from 27/32 to 32/32;
- response-validation failures decreased from 5 to 0;
- answerability accuracy increased from 0.6250 to 0.7812;
- valid refusal of unsupported controls increased from 0/12 to 5/12;
- answerable formal claims increased from 21 to 33;
- claims per answerable query increased from 1.05 to 1.65.

The adapter did not solve unsupported-premise acceptance completely. Seven of twelve unsupported controls were still answered rather than refused.

## Adapter effect within grounded RAG

With the grounded-RAG system held fixed:

- both Base and LoRA completed 32/32 queries;
- both achieved perfect unsupported-refusal behavior on the protected controls;
- both retained 0.9310 exact expected-term recall;
- answerable formal claims increased from 32 to 53 with LoRA;
- claims per answerable query increased from 1.60 to 2.65.

The adapter therefore primarily changed response decomposition after the grounding system had already established a reliable evidence boundary.

## Grounded-system effect

Neither closed-book condition matched the reliability of the grounded-RAG system.

The full grounded path combines:

- retrieval;
- reranking;
- evidence-sufficiency assessment;
- grounded structured generation;
- evidence-ID validation;
- application-side citation resolution.

Both grounded configurations correctly handled all unsupported controls in the protected benchmark.

This suggests that evidence sufficiency and grounded generation provide a reliability boundary that model adaptation alone did not reproduce.

## Metric limitation

Exact expected-term recall was 0.9310 in all four conditions.

This metric captures lexical concept presence, not:

- factual correctness;
- claim support;
- semantic equivalence;
- hallucinated details;
- completeness;
- redundancy.

The four-way study therefore motivates a semantic and claim-level evaluation phase.

## Important caveats

Closed-book and grounded-RAG conditions do not use identical prompt contracts, because the grounded conditions require evidence references and citations while closed-book generation does not.

Comparisons of Base versus LoRA within the same system condition are therefore the cleanest adapter ablations.

Cross-system comparisons should be interpreted as system-level behavior rather than as the isolated effect of retrieval alone.

Base closed-book token totals exclude provider usage from the five responses that failed post-generation response validation. Token totals should therefore not be directly compared with the complete LoRA closed-book totals.

## Next experiment

The next evaluation phase should examine whether increased formal-claim decomposition corresponds to improved technical quality.

Planned evaluation:

- semantic expected-concept matching;
- claim-evidence entailment for RAG responses;
- answer-to-claim completeness;
- redundancy analysis;
- targeted human review.

Only after this semantic-quality layer is established should AeroRAG-X move to bounded adaptive retrieval.
