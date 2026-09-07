# Adaptive evidence budget v0.5

## Motivation

Fixed top-3 saved roughly one-third of total tokens in two development runs and
the frozen final validation, but the final validation rejected it because three
answerable queries became refusals and one response failed validation. Fixed
top-5 retained quality but always paid the larger prompt cost.

## Policy

The candidate retrieves and reranks no more than five passages. Before model
generation, it evaluates only the first three with the existing deterministic
sufficiency assessor.

- If the first three are sufficient, it sends three.
- If they have a recoverable evidence-count or query-coverage gap, it sends five.
- If they are missing a numeric, named, claim, or universal-scope anchor, it
  retains three rather than adding merely topical evidence.
- It never expands after seeing a model response.
- It never exceeds five passages.

Every query receives an auditable decision containing the requested and
selected depths, initial reasons, expansion flag, and expansion reason.

## Evaluation order

`scripts/run_adaptive_context_dev_v0_5.sh` runs fixed top-5, fixed top-3, and
adaptive 3→5 on the same 50 development cases. The promotion decision compares
adaptive with fixed top-5 and requires at least 15% paired total-token savings,
at least 25 paired calls, no additional failures, and no quality-rate regression
larger than 0.02.

This is development-only. The completed 32-query v0.4.2 result must not be
reused to tune or validate v0.5. A passing development result requires a newly
versioned held-out set before any final adaptive-policy claim.
