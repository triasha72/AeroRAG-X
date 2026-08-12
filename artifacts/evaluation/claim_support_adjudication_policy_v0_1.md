# Claim-Support Adjudication Policy v0.1

## Scope

This evaluation determines whether each formal grounded claim is
supported by the evidence cited by that claim.

Only the cited evidence is considered.

No external knowledge, uncited retrieval results, or assumptions
about the underlying source document may be used to assign a label.

If a claim cites multiple evidence records, those records may be
considered jointly.

## Labels

### SUPPORTED

Use `SUPPORTED` when the cited evidence directly states or clearly
entails all material parts of the formal claim.

Minor paraphrasing, compression, reordering, or terminology changes
are acceptable if the technical proposition remains unchanged.

### PARTIALLY_SUPPORTED

Use `PARTIALLY_SUPPORTED` when the evidence establishes a
substantive part of the claim but does not establish the complete
proposition.

Examples include:

- an additional unsupported qualifier;
- an unsupported causal relationship;
- an unsupported quantitative statement;
- an unsupported generalization;
- combining one supported proposition with another unsupported one.

### UNSUPPORTED

Use `UNSUPPORTED` when the evidence may be topically related but
does not establish the central proposition expressed by the claim.

Do not count keyword or subject overlap as support.

### CONTRADICTED

Use `CONTRADICTED` when the cited evidence materially conflicts
with the claim.

The evidence must support a proposition incompatible with the
formal claim; absence of evidence alone is not contradiction.

## Decision rules

1. Evaluate the formal claim, not the prose answer.
2. Evaluate only evidence cited by that formal claim.
3. Multiple cited chunks may be considered jointly.
4. Do not reward a claim simply because it is plausible.
5. Do not use outside technical knowledge to fill evidence gaps.
6. Preserve partial support rather than forcing borderline claims
   into SUPPORTED.
7. Use UNSUPPORTED when no material part of the central proposition
   is actually established.
8. Use CONTRADICTED only for genuine conflict, not omission.
9. Exact normalized claim containment previously classified as
   `AUTO_SUPPORTED_EXACT` remains `SUPPORTED`.
10. Record a short adjudication note for every manually reviewed
    claim.

## Reporting

Two support rates will be reported:

- strict support rate:
  `SUPPORTED / all claims`
- support-or-partial rate:
  `(SUPPORTED + PARTIALLY_SUPPORTED) / all claims`

`UNSUPPORTED` and `CONTRADICTED` remain separate failure categories.
