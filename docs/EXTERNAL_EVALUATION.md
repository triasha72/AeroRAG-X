# External evaluation

The public retrieval checks in this repository are useful, but they do not replace a new question set written by somebody who did not build the system.

## Before the run

The evaluator picks NASA reports, writes questions, and records their expected answer, needed facts, supporting pages, and answerability label. They do this before looking at any AeroRAG-X output.

The system owner records the commit, corpus and index files, model settings, thresholds, and provider settings. Those inputs are hashed by `run_external_evaluation_v0_1.py`.

## What to score

For an answerable question, score the answer as correct, partly correct, or incorrect. Check each factual claim against the page cited for it.

For a question the corpus cannot answer, a good response says the evidence is not enough or asks for missing context. A made-up answer is a failure.

Use these labels when useful:

- `R1`: source not retrieved
- `R2`: source retrieved too low
- `R3`: enough evidence rejected
- `R4`: weak evidence accepted
- `G1`: evidence ignored
- `G2`: unsupported detail added
- `G3`: number wrong
- `G4`: unit wrong
- `G5`: condition missing
- `C1`: citation wrong
- `C2`: citation only partly supports the claim
- `C3`: citation missing
- `A1`: ambiguous question handled badly
- `F1`: unsupported question answered
- `F2`: answerable question refused

## After the baseline

The evaluator shares the completed score sheet and failures. Changes to the system produce v2. The evaluator then writes a new holdout set for v2; the old set is not the final check.
