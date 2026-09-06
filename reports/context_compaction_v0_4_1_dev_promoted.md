# Context compaction v0.4.1 — 50-case development gate passed

## Outcome

The larger development comparison passed every predeclared gate. Holding the
epoch-2 LoRA checkpoint, v0.3.1 prompt, retrieval candidate pool, generation
settings, and query order fixed, reducing final evidence from five passages to
three lowered paired mean total tokens by **31.94%**.

| Metric | Top 5 control | Top 3 treatment |
|---|---:|---:|
| Completed queries | 47/50 | 48/50 |
| Generation failures | 3 | 2 |
| Answerability accuracy | 0.8800 | 0.9000 |
| Answerable completion | 0.9211 | 0.9211 |
| Unsupported refusal | 0.7500 | 0.8333 |
| Expected-term recall | 0.4857 | 0.5286 |
| Structural validity | 0.9400 | 0.9600 |
| Citation/source metrics | 1.0000 | 1.0000 |

Forty calls had token observations in both arms. Mean paired input tokens fell
from 2,304.10 to 1,523.45 (-33.88%), output tokens fell from 160.20 to 153.70
(-4.06%), and total tokens fell from 2,464.30 to 1,677.15 (-31.94%). The
output-token bootstrap interval crossed zero, so the defensible efficiency
claim is input and total-token reduction, not a proven output-length effect.

## Why this advances

Every gate passed: all 50 cases were represented, failures did not increase,
each quality rate stayed within the frozen 0.02 bound, paired calls exceeded
25, and total-token reduction exceeded 15%. This independently reproduces the
direction and approximate size of the earlier eight-case development result.

## Evidence boundary

This remains development evidence. Thirty-two cases are deterministic
source-grounded stress cases without independent human review. The set is
checksum-locked and disjoint by normalized text and ID from the repository's
protected/held-out generation sets, but its metrics are not a substitute for
human semantic adjudication.

Control report SHA-256:
`00b655a63eef765dae66848cf069b6d72c3da874c8c169951a77e9ac8ec2d466`

Treatment report SHA-256:
`9f2c68c6432ef376eb3580a6215d11cd92fa003666c971cdcad0291eea361f61`

Paired analysis SHA-256:
`53bd4e0c1361e490f1f3bc8e8eb5eee549d2fbe05267c6d0d72deb99e9e7a3a3`

Decision SHA-256:
`49dc3d5bc86ddced58f9aa93a1fc5085e8782e2373cd49eea53d1626e2f6eac8`
