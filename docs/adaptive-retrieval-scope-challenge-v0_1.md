# Adaptive-retrieval unsupported-scope challenge v0.1

## Purpose

This development-only challenge set evaluates whether bounded adaptive retrieval
incorrectly treats topically related evidence as support for a broader claim.

It was created after the Phase 26 held-out evaluation identified an
unsupported-scope regression. It is separate from the protected Phase 26
held-out query set and must not replace, modify, or be merged into that set.

## Dataset

`data/evaluation/adaptive_scope_challenge_v0_1.jsonl` contains:

- 10 independently authored unanswerable queries covering universal claims,
  mandatory requirements, regulatory overclaims, future speculation, and
  fictional entities.
- 4 answerable control queries covering supported aerospace topics.

## Evaluation questions

For each unanswerable query, assess whether the system:

1. identifies that retrieved evidence is insufficient for the full claim;
2. refuses rather than generating a topically related answer;
3. preserves bounded retrieval behavior and evidence provenance.

For each answerable control query, assess whether the system still produces a
grounded response with expected terminology and valid citations.

## Constraints

- Do not modify Phase 26 held-out queries, labels, artifacts, thresholds,
  retrieval settings, sufficiency settings, or decision rules.
- Do not add Phase 26 held-out questions to this development dataset.
- Do not change the adaptive retrieval policy until baseline behavior on this
  new development set has been recorded.
- Any later policy change must be evaluated first on this development set and
  then on a newly versioned held-out evaluation.

## Initial success criteria

Before proposing a new held-out evaluation:

- All 10 unsupported-scope queries should receive grounded refusals.
- The four answerable controls should remain answerable.
- Retrieval must remain bounded to two passes and one deterministic rewrite.
- Provenance and trace validation must remain valid for every query.