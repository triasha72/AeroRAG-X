# Qwen Four-Way System Study — v0.2

## Purpose

This study compares Base and LoRA-adapted Qwen generation with and without the AeroRAG-X grounded evidence pipeline.

The four conditions are:

1. Base Qwen closed-book
2. LoRA-adapted Qwen closed-book
3. Base Qwen with grounded RAG
4. LoRA-adapted Qwen with grounded RAG

The grounded-RAG conditions include retrieval, reranking, evidence-sufficiency assessment, grounded structured generation, citation validation, and application-side evidence resolution.

Cross-system comparisons should therefore be interpreted as system-level ablations rather than the isolated effect of retrieval.

## Evaluation correction from v0.1

The initial closed-book v0.1 evaluation treated five Base outputs as response-validation failures.

Raw-payload analysis showed that those outputs were semantic refusal attempts:

- four used the canonical refusal answer with `insufficient_knowledge=true` but also emitted explanatory claims;
- one used the canonical refusal answer with an empty claims array but omitted the `insufficient_knowledge` field.

A narrow normalization layer was therefore introduced for v0.2.

Only the exact canonical refusal sentence is normalized:

- missing `insufficient_knowledge` is recovered as `true`;
- claims are removed when the canonical refusal is represented with `insufficient_knowledge=true`;
- unrelated malformed responses remain invalid.

The original v0.1 artifacts are retained as evidence of raw structured-output compliance.

## Corrected aggregate results

| Metric | Base closed-book | LoRA closed-book | Base + grounded RAG | LoRA + grounded RAG |
|---|---:|---:|---:|---:|
| Completed | 32/32 | 32/32 | 32/32 | 32/32 |
| Generation failures | 0 | 0 | 0 | 0 |
| Answerability accuracy | 0.7812 | 0.7812 | 1.0000 | 1.0000 |
| Strict unsupported refusal | 0.4167 | 0.4167 | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Formal answerable claims | 21 | 33 | 32 | 53 |
| Claims / answerable query | 1.05 | 1.65 | 1.60 | 2.65 |

## LoRA effect in closed-book generation

After canonical-refusal normalization, Base and LoRA have the same benchmark-level:

- completion;
- generation reliability;
- answerability accuracy;
- strict refusal rate;
- lexical expected-term recall.

The main observed difference is response decomposition.

Formal answerable claims increase:

- Base: 21
- LoRA: 33

This is a 57.1% increase in formal claim count.

The result supports the interpretation that the LoRA adapter primarily changes structured technical decomposition rather than benchmark-level closed-book refusal behavior.

## LoRA effect within grounded RAG

With the grounded system held fixed:

- Base + RAG: 32 formal claims
- LoRA + RAG: 53 formal claims

This is a 65.6% increase.

Both grounded conditions retain:

- 32/32 completion;
- zero failures;
- 1.0000 answerability;
- 1.0000 unsupported refusal;
- 0.9310 lexical expected-term recall.

This suggests that LoRA continues to affect response decomposition after grounding has established the reliability boundary.

## Grounded-system effect

The largest reliability difference occurs between closed-book and grounded generation.

Closed-book:

- answerability accuracy: 0.7812
- strict unsupported refusal: 0.4167

Grounded RAG:

- answerability accuracy: 1.0000
- strict unsupported refusal: 1.0000

The grounded system includes more than retrieval alone. It combines:

- sparse and dense retrieval;
- rank fusion;
- reranking;
- evidence-sufficiency assessment;
- grounded structured generation;
- evidence-ID validation;
- citation resolution.

The result therefore supports a system-level conclusion:

The grounded evidence pipeline provides a stronger unsupported-query reliability boundary than model adaptation alone on this protected benchmark.

## Metric limitation

Expected-term recall is 0.9310 in all four conditions despite substantial differences in system behavior and formal claim decomposition.

This demonstrates that lexical expected-term recall alone cannot distinguish:

- factual correctness;
- semantic equivalence;
- claim support;
- unsupported details;
- answer completeness;
- redundancy;
- technical quality.

A stronger semantic and claim-level evaluation layer is therefore required before adding substantially more orchestration complexity.

## Next phase

The next evaluation phase should measure:

1. semantic expected-concept coverage;
2. claim-evidence entailment;
3. answer-to-claim completeness;
4. unsupported-response taxonomy;
5. redundancy;
6. targeted human review.

Bounded adaptive retrieval should follow only after the evaluation layer can distinguish technical-quality differences that lexical recall currently misses.
