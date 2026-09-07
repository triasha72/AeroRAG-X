# Adaptive evidence budget v0.5 — development no-op rejection

The three-arm run completed, but the adaptive candidate did not demonstrate an
adaptive recovery effect. Its generation report was byte-identical to fixed
top-3. Of 50 queries, 49 retained three passages and only one expanded to five;
that expanded case remained insufficient and produced the same refusal and
token count under both policies.

The original generic efficiency gate printed `promoted` because adaptive
matched fixed top-3 quality while saving 31.94% versus top-5. That gate did not
test whether the adaptive branch was active. The follow-up policy-activity gate
correctly rejected the candidate because it had fewer than three expansions,
zero effective higher-input cases versus fixed top-3, and its sole expansion
did not recover sufficiency.

A retrieval-backed scan of 478 unused automatic source candidates found only
one top-3-insufficient/top-5-sufficient case. The available development corpus
therefore does not support a meaningful 3→5 recovery study. The project does
not manufacture cases or reuse the completed protected set to make the policy
look adaptive.

Engineering decision: retain fixed uncompressed top-5 as the default, preserve
fixed top-3 and adaptive v0.5 as rejected results, and test query-aware
extractive compression within all five passages. This keeps source breadth—the
dimension lost by top-3—while targeting redundant prompt text.

The immutable artifact inventory and checksums are recorded in
`artifacts/evaluation/generation_lora_adaptive_context_dev_v0_5_manifest.json`.
The manifest deliberately labels the run `completed_rejected_noop`; completion
of a benchmark is not the same as validation of its hypothesis.
