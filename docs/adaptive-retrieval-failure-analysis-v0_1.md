# Adaptive-retrieval failure analysis v0.1

## Scope

This document analyzes the Phase 26 adaptive-retrieval regression without
changing the protected held-out v0.4 queries, labels, thresholds, retrieval
settings, sufficiency settings, or Phase 25 policy.

## Observed regression

- Protected baseline parity: PASS
- Answerability accuracy: 91.67% single pass vs 83.33% bounded adaptive
- Unsupported refusal: 83.33% single pass vs 66.67% bounded adaptive
- Failing held-out query: `heldout_scope_002`
- Failure type: recovered evidence was assessed as sufficient for an
  unanswerable universal scope claim.

## Evidence chain

Record the original query, deterministic rewritten query, both sufficiency
assessments, reasons, and retrieved source identifiers from the Phase 26
artifacts.

## Initial hypothesis

The deterministic rewrite increased lexical overlap with broad aircraft,
battery, and weather terms without establishing support for the question's
universal claim. The evidence-sufficiency gate measured topical support but
did not reject unsupported universal quantification or scope expansion.

## Constraints

- Do not alter Phase 26 held-out data or use this query to tune thresholds.
- Keep bounded adaptive retrieval opt-in.
- Validate any future policy change on a newly authored development challenge
  set before a fresh, separately versioned held-out evaluation.

## Next experiment

Create a development-only unsupported-scope challenge set containing new,
independently authored questions with universal claims, mandatory conditions,
future speculation, fictional entities, and regulatory overclaims.