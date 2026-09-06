# Concise generation v0.3.2 — development rejection

v0.3.2 tested whether stricter answer and claim limits could deliver the token
reduction that v0.3.1 did not. It held the frozen epoch-2 LoRA control,
development queries, retrieval settings, and structured response contract
fixed, while limiting answers to 80 words, preferring one claim, allowing at
most two claims, and reducing the output ceiling to 256 tokens.

The real MPS treatment completed seven of eight queries. The failed query ended
after 23 output tokens with malformed JSON; it did not reach the token ceiling.
The candidate therefore introduced a reliability regression rather than merely
exposing an overly small output budget.

| Metric | Original LoRA control | v0.3.2 concise |
|---|---:|---:|
| Completed | 8 / 8 | 7 / 8 |
| Generation failures | 0 | 1 |
| Answerability accuracy | 1.0000 | 0.8750 |
| Answerable completion | 1.0000 | 0.8333 |
| Unsupported refusal | 1.0000 | 1.0000 |
| Expected-term recall | 0.8889 | 0.6667 |
| Structural validity | 1.0000 | 0.8750 |

Across six successful provider-called pairs, mean output fell by 6.18% and mean
total tokens fell by 2.96%. The output-token bootstrap interval was [-59.50,
+33.50] tokens. The candidate failed the reliability, quality, sample-size, and
15% token-reduction gates and is rejected. It must not be run on the protected
set.

This result also changes the engineering direction. Output is a small part of
the full request budget, and increasingly strict wording did not reliably make
the model concise. The next development experiment keeps the structurally
reliable v0.3.1 prompt and reduces evidence from five passages to three. That
isolates context compression and gates on total tokens plus unchanged quality.

## Artifact identity

- Treatment report: `e22f1e806de545b1808731001bde042445a1c9756c5b98d767211cd145f4ede8`
- Treatment telemetry: `02f60899f3f93f014243ff5d60b57d5c83941f6665ae3c6e80c076d34416b8ac`
- Paired analysis: `1a5b9bbb05a03eee4a12fa9c8f7cee6d54078d0ce5bc4b376c19ec85980edfb0`
- Fail-closed decision: `a85bab04e12b9947c32e72da354379b26920b507d4a2907c0dd8eb7b7e997c18`
