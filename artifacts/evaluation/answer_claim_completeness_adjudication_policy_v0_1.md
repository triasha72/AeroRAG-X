# Answer-to-Claim Completeness Adjudication Policy v0.1

## Scope

This evaluation measures whether the formal claim structure captures the
material factual and technical propositions expressed in the prose answer.

This is a representation/completeness evaluation. It does not re-evaluate
whether the answer is factually correct or whether the cited evidence supports
the claims. Claim-evidence support is evaluated separately.

## Review inputs

For each grounded answer, review only:

- the user query;
- the prose answer;
- the formal claims generated for that answer.

The cited evidence is not needed for this evaluation.

## Labels

### FULLY_CAPTURED

Use `FULLY_CAPTURED` when every material factual or technical proposition in
the prose answer is represented by one or more formal claims.

Exact wording is not required. Paraphrase, compression, splitting, and
reordering are acceptable when the technical meaning is preserved.

### PARTIALLY_CAPTURED

Use `PARTIALLY_CAPTURED` when the formal claims capture the central answer but
omit one or more secondary substantive propositions, qualifications,
mechanisms, or quantitative details.

The omission must be meaningful, not merely stylistic.

### MATERIAL_OMISSION

Use `MATERIAL_OMISSION` when a central proposition or important qualification
in the prose answer is absent from the formal claims, such that the formal
claim structure materially under-represents the answer.

## Decision rules

1. Evaluate answer-to-claim coverage, not factual correctness.
2. Do not use external knowledge.
3. Do not use cited evidence to fill gaps in the formal claims.
4. Ignore purely stylistic or discourse text.
5. Treat semantically equivalent paraphrases as captured.
6. A proposition may be covered jointly by multiple formal claims.
7. A formal claim may cover multiple propositions from the answer.
8. Quantitative details count when they materially contribute to the answer.
9. Do not penalize extra formal claims in this evaluation; redundancy is
   evaluated separately.
10. Record a short adjudication note for every reviewed unit.

## Reporting

Report, separately for Base + RAG and LoRA + RAG:

- total answer count;
- `FULLY_CAPTURED`;
- `PARTIALLY_CAPTURED`;
- `MATERIAL_OMISSION`;
- full-capture rate;
- full-or-partial capture rate.

This is a single structured adjudication pass under a frozen policy, not an
independent multi-assessor human annotation study.
