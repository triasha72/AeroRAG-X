# Untuned Local Transformers Baseline Analysis

## Overview

This report analyzes the untuned local Transformers generation baseline for AeroRAG-X.

The experiment evaluates `Qwen/Qwen3-0.6B` as the local generation model within the existing evidence-grounded RAG pipeline.

The purpose of this baseline is to measure local-model generation quality before any PEFT/LoRA adaptation or inference optimization.

## Configuration

- Generation model: `Qwen/Qwen3-0.6B`
- Provider: local Hugging Face Transformers
- Dense backend: NumPy
- Reranker: `cross-encoder/ms-marco-MiniLM-L6-v2`
- Candidate top-k: 20
- Evidence top-k: 5
- Sampling: disabled
- External API-token cost: $0
- Evaluation set: `generation_queries_v0_3.jsonl`

## Evaluation Set

- Total queries: 32
- Answerable queries: 20
- Unsupported queries: 12

## Baseline Results

| Metric | Qwen 0.6B local |
|---|---:|
| Completed queries | 32 / 32 |
| Generation failures | 0 |
| Generation failure rate | 0.0000 |
| Answerability accuracy | 1.0000 |
| Answerable completion | 1.0000 |
| Unsupported refusal | 1.0000 |
| Claim citation coverage | 1.0000 |
| Citation-reference validity | 1.0000 |
| Source-document coverage | 1.0000 |
| Structural validity | 1.0000 |
| Expected-term recall | 0.9138 |
| Matched expected terms | 53 / 58 |

The local model completed all evaluation queries without a structured-generation failure.

All unsupported requests were rejected correctly by the evidence-sufficiency path, and all generated claims satisfied the current citation and structural checks.

## Provider Telemetry

| Metric | Value |
|---|---:|
| Provider calls | 20 |
| Provider bypasses | 12 |
| Unknown call states | 0 |
| Call-policy accuracy | 1.0000 |
| Provider retries | 0 |
| Input tokens | 49,589 |
| Output tokens | 2,969 |
| Total tokens | 52,558 |
| External API cost | $0 |
| Mean generation latency | 14.29 s |
| P50 generation latency | 7.87 s |
| P95 generation latency | 29.26 s |

The local model therefore removes external inference-token cost, but currently has substantially higher tail latency than the remote-provider baseline.

## Expected-Term Miss Analysis

The exact lexical expected-term metric identified five queries with recall below 1.0.

| Query | Missing term | Manual classification | Interpretation |
|---|---|---|---|
| `core_008` | `detection` | Lexical-equivalent | The answer uses `detected` and describes precursor detection; this is primarily an exact-word-matching limitation. |
| `para_001` | `cell` | Genuine content omission | The answer explains dendrite-induced internal short circuits and runaway initiation but does not adequately explain propagation from one cell to neighboring cells. |
| `para_005` | `distributed` | Lexical/semantic-equivalent | The answer describes distributing power across the airframe but does not use the exact expected form `distributed`. |
| `para_009` | `detection` | Lexical-equivalent | The answer explicitly uses `detect` and identifies ultrasonic NDE and related detection methods. |
| `synth_003` | `safety` | Semantic-equivalent / compressed | The answer discusses faults, degradation, failure modes, sensing, and health management but does not use the exact word `safety`. |

Four of the five exact-term misses therefore appear primarily related to lexical or semantic equivalence rather than clear factual omissions.

`para_001` is the clearest genuine content-coverage weakness.

## Claim-Decomposition Observation

The stronger difference between the local Qwen baseline and the OpenAI baseline is response decomposition.

The local Qwen baseline produced:

- 25 claims
- 31 citations
- 33 citation references

across 20 answerable queries.

This corresponds to approximately:

- 1.25 claims per answerable query

The existing OpenAI v0.3 baseline produced:

- 101 claims
- 82 citations
- 149 citation references

across the same 20 answerable queries.

This corresponds to approximately:

- 5.05 claims per answerable query

The local model therefore tends to compress several technical statements into a small number of formal claims.

The current structural-validity metric does not penalize this behavior because each claim that is produced is correctly cited and source-backed.

This is an important evaluation limitation and a useful target for subsequent model adaptation.

## Comparison with OpenAI Baseline

| Metric | OpenAI v0.3 | Qwen 0.6B local |
|---|---:|---:|
| Answerability accuracy | 1.0000 | 1.0000 |
| Answerable completion | 1.0000 | 1.0000 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Claim citation coverage | 1.0000 | 1.0000 |
| Citation-reference validity | 1.0000 | 1.0000 |
| Source-document coverage | 1.0000 | 1.0000 |
| Structural validity | 1.0000 | 1.0000 |
| Expected-term recall | 0.9310 | 0.9138 |
| Total claims | 101 | 25 |
| Total citations | 82 | 31 |
| Total citation references | 149 | 33 |
| Provider calls | 20 | 20 |
| Provider bypasses | 12 | 12 |
| Retry rate | 0.0000 | 0.0000 |
| P50 generation latency | 5.64 s | 7.87 s |
| P95 generation latency | 7.69 s | 29.26 s |
| External inference cost | $0.103745 | $0 |

## Interpretation

The untuned 0.6B local model performs substantially better than its size alone might suggest on the current grounded-generation benchmark.

It preserves the tested answerability, refusal, citation-validity, source-grounding, and structural properties of the larger remote-provider baseline while eliminating external inference-token cost.

The primary observed weaknesses are:

1. lower exact expected-term recall;
2. substantially less granular claim decomposition;
3. higher generation latency, particularly tail latency.

Most exact expected-term misses are lexical or semantic variants rather than clear factual failures.

The most meaningful generation-quality weakness is the tendency to compress multiple technical facts into a small number of formal claims and citations.

## Implications for LoRA

The baseline does not provide evidence that LoRA is needed to repair JSON formatting, citation validity, refusal behavior, or basic structured generation.

A more defensible LoRA objective is:

> Improve grounded technical completeness and claim decomposition while preserving the existing refusal, citation-validity, structural-validity, and generation-reliability performance.

Training and development data must remain separate from the frozen 32-query evaluation set.

The evaluation queries and their reference outcomes should not be used directly as LoRA training examples.

## Implications for Efficient Inference

Latency is the main systems-level weakness of the local baseline.

Future inference experiments should measure:

- P50 latency
- P95 latency
- tokens per second
- memory usage
- generation failure rate
- grounding metrics
- structural validity

under reduced-precision or quantized inference configurations.

No Qualcomm hardware-performance claim should be made unless the model is actually benchmarked on Qualcomm hardware.

## Baseline Status

This baseline is frozen before:

- PEFT/LoRA adaptation
- prompt tuning
- retrieval tuning
- sufficiency-threshold tuning
- quantization
- reduced-precision benchmarking
- agent-system development

The frozen JSON artifacts should remain unchanged for future comparisons.
