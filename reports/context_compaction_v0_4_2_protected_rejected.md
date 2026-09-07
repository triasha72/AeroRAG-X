# Fixed top-3 context v0.4.2 — frozen final-validation rejection

## Decision

The one-shot run completed and the fixed three-passage policy was rejected. It
reproduced substantial token savings, but it crossed the frozen answerable
quality and failure boundaries. The outcome is preserved without threshold
changes or a selective rerun.

| Metric | Top 5 control | Top 3 treatment |
|---|---:|---:|
| Completed queries | 32/32 | 31/32 |
| Generation failures | 0 | 1 |
| Answerability accuracy | 0.9062 | 0.8750 |
| Answerable completion | 0.9500 | 0.8000 |
| Unsupported refusal | 0.8333 | 1.0000 |
| Expected-term recall | 0.9138 | 0.7414 |
| Structural validity | 1.0000 | 0.9688 |
| Citation/source metrics | 1.0000 | 1.0000 |

Across 16 paired provider calls, input tokens fell 36.33% and total tokens fell
33.20%. Output tokens increased 4.64%, with a bootstrap interval spanning zero.
The policy therefore demonstrated an input-cost benefit, not an output-token
benefit.

The gate failed because answerable completion fell by 0.15, expected-term
recall fell by 0.1724, and failures increased from zero to one. Three previously
answerable questions became refusals; the failed `para_003` response exceeded
the claim limit. Two unsupported questions improved from answers to refusals.
This pattern shows that a smaller context makes the system more conservative,
which helps unsupported cases but removes necessary support for some answerable
cases.

## Engineering consequence

Fixed top-5 remains the safe default. Fixed top-3 remains rejected. The next
development hypothesis is a pre-generation adaptive 3→5 budget: retain three
when evidence is sufficient or contains hard unsupported signals, and expand to
five only for recoverable lexical coverage gaps. No model-output retry is
allowed.

The final manifest status is `completed_rejected`; its protocol and every output
are checksum-bound in
`artifacts/evaluation/generation_lora_context3_protected_v0_4_2_manifest.json`.
