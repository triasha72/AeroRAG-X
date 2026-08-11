# Base+RAG vs LoRA+RAG — Protected Benchmark v0.3

## Experimental design

Both conditions use the same frozen 32-query benchmark, retrieval stack, reranker, evidence-sufficiency policy, prompt version, generation budget, and deterministic generation configuration.

The model-side intervention is the presence or absence of the trained PEFT/LoRA adapter.

## Aggregate results

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Completed queries | 32/32 | 32/32 |
| Generation failures | 0 | 0 |
| Answerability accuracy | 1.0000 | 1.0000 |
| Answerable completion | 1.0000 | 1.0000 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 |
| Citation validity | 1.0000 | 1.0000 |
| Source-document coverage | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9310 |
| Structural validity | 1.0000 | 1.0000 |
| Formal claims | 32 | 53 |
| Claims / answerable query | 1.600 | 2.650 |
| P50 provider latency | 8.877 s | 14.873 s |
| P95 provider latency | 16.085 s | 19.127 s |
| Provider output tokens | 3314 | 5182 |

## Interpretation

The final robustness fixes restored complete reliability: both Base+RAG and LoRA+RAG completed all protected queries with no generation failures.

The adapter preserved answerability, refusal behavior, citation validity, source grounding, expected-term recall, and structural validity.

LoRA output is evaluated separately for technical decomposition and verbosity rather than treating longer responses as inherently better.

## Engineering progression

The LoRA evaluation exposed structured-generation failure modes including output truncation, supported responses with missing claims, and duplicate evidence references.

These were addressed with a larger bounded generation budget, a hardened structured-output prompt, and deterministic duplicate-evidence normalization while retaining strict unknown-evidence validation.

## Conclusion

The final protected benchmark demonstrates that the adapted local model can run through the production grounded-RAG path without sacrificing the system's refusal, grounding, citation, or structural-response guarantees.
