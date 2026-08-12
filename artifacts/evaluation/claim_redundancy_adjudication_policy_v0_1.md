# Claim Redundancy Adjudication Policy v0.1

## Scope

This evaluation measures semantic redundancy among formal claims generated
within the same grounded answer.

It does not evaluate factual correctness, evidence support, or answer
completeness. Those properties are evaluated separately.

## Review inputs

For each answer, review:

- the query;
- the prose answer for context;
- all formal claims generated for that answer.

Compare claims only with other claims from the same answer.

## Labels

### DISTINCT

Use `DISTINCT` when the claim contributes a substantive proposition that is
not materially repeated or subsumed by another formal claim in the same answer.

A claim can share topic vocabulary with another claim and still be `DISTINCT`
when it contributes a different technical proposition.

### OVERLAPPING

Use `OVERLAPPING` when the claim shares a substantive proposition with one or
more sibling claims but also contributes material information that is not
contained in those sibling claims.

Overlap is not treated as full redundancy.

### REDUNDANT

Use `REDUNDANT` when the material proposition of the claim is already fully
captured by one or more sibling claims in the same answer, so removing the
claim would not materially reduce the formal claim structure's information.

A narrower restatement that adds no material information may be redundant.

## Decision rules

1. Compare claims only within the same answer.
2. Evaluate semantic content, not exact wording.
3. Do not use outside knowledge.
4. Do not use citation evidence to decide redundancy.
5. Topic similarity alone is not overlap.
6. Partial shared content plus additional material content is `OVERLAPPING`.
7. Full semantic subsumption with no material addition is `REDUNDANT`.
8. Claims in a single-claim answer are deterministically `DISTINCT`.
9. When marking `OVERLAPPING` or `REDUNDANT`, identify the related sibling
   claim IDs.
10. Record a short note for every manually reviewed claim.

## Reporting

Report separately for Base + RAG and LoRA + RAG:

- total claims;
- distinct claims;
- overlapping claims;
- redundant claims;
- redundancy rate = redundant / total claims;
- overlap rate = overlapping / total claims;
- nonredundant rate = (distinct + overlapping) / total claims.

Do not interpret a higher raw claim count as higher quality by itself.

This is a single structured adjudication pass under a frozen policy, not an
independent multi-assessor human annotation study.
