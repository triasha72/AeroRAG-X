# Phase 26 bounded adaptive-retrieval evaluation v0.1

## Scope

This paired study compares frozen single-pass retrieval with the Phase 25 bounded adaptive policy on the protected held-out v0.4 query set. The adaptive policy permits at most two retrieval passes and one deterministic rewrite.

## Protocol integrity

- Protected baseline parity: **PASS**
- Adaptive trace validity: **PASS**
- Adaptive provenance validity: **PASS**
- Retrieval bounds respected: **PASS**
- Predeclared quality improvement: **FAIL**

## Generation and grounding metrics

| Metric | Single pass | Bounded adaptive | Adaptive - single pass |
|---|---:|---:|---:|
| Answerability accuracy | 91.67% | 83.33% | -8.33 pp |
| Answerable completion | 100.00% | 100.00% | +0.00 pp |
| Unsupported refusal | 83.33% | 66.67% | -16.67 pp |
| Citation-reference validity | 100.00% | 100.00% | +0.00 pp |
| Structural validity | 100.00% | 100.00% | +0.00 pp |
| Expected-term recall | 77.78% | 77.78% | +0.00 pp |

## Adaptive-retrieval behavior

| Metric | Value |
|---|---:|
| Recovery triggers | 5 |
| Successful recoveries | 1 |
| Recovery grounded refusals | 4 |
| Total retrieval attempts | 17 |
| Total query rewrites | 5 |

## Latency

| Metric | Single pass | Bounded adaptive | Adaptive - single pass |
|---|---:|---:|---:|
| Mean total latency | 805.504 ms | 990.612 ms | +185.108 ms |
| P95 total latency | 898.159 ms | 1441.129 ms | +542.970 ms |
| Mean retrieval latency | 803.398 ms | 987.881 ms | +184.483 ms |

## Decision

**Verdict: `integrity_regression`**

The bounded policy violated a predeclared integrity or grounding non-regression condition.

## Guardrails

- The protected held-out query set, labels, retrieval settings, sufficiency settings, and decision rules were not tuned after observing this run.
- A successful recovery means the first assessment was insufficient and the second assessment was sufficient.
- Results report this fixed policy; they do not establish universal retrieval quality.
