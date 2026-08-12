# Phase 26 bounded adaptive-retrieval evaluation

Phase 26 is one protected paired study. It compares the frozen one-pass
system with the Phase 25 bounded adaptive-retrieval policy on the same held-out
v0.4 query set.

## What the runner protects

Before it issues a held-out query, the runner checks that:

- all declared inputs are present;
- the held-out queries, baseline report, protected Phase 25 manifest, and
  retrieval / generation configuration hashes match the frozen protocol;
- the Phase 25 manifest still validates its own protected inputs;
- both conditions use the same generation, reranker, candidate-depth, and
  evidence-depth settings;
- only the bounded adaptive condition enables the recovery policy;
- the adaptive policy remains limited to two retrieval attempts and one
  deterministic rewrite.

The local corpus chunks and embedding artifacts are checksummed in the output
manifest. They are normally generated files, so the output records their exact
local versions even though they are not committed to the repository.

## Run the study

Activate the existing project environment and run the evaluator exactly once:

```bash
cd ~/Downloads/AeroRAG-X
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate aeroragx-py312
PYTHONPATH=src python scripts/run_adaptive_retrieval_evaluation_v01.py
```

Do not change the held-out queries, labels, retrieval settings, sufficiency
settings, model settings, or Phase 25 policy after seeing this result. If an
output already exists, the command stops rather than replacing it. Use
`--overwrite` only when intentionally replacing a documented prior run.

## Outputs

The runner writes these artifacts:

- `artifacts/evaluation/adaptive_retrieval_v0_1_inputs.sha256` — exact files
  used for the run;
- `artifacts/evaluation/adaptive_retrieval_v0_1_baseline.json` — fresh
  single-pass condition;
- `artifacts/evaluation/adaptive_retrieval_v0_1_adaptive.json` — bounded
  adaptive condition, including per-query trace and timing diagnostics;
- `artifacts/evaluation/adaptive_retrieval_v0_1_comparison.json` — paired
  deltas, baseline parity, safety checks, and verdict;
- `reports/adaptive_retrieval_v0_1.md` — concise human-readable report.

Measured query latency excludes one-time runtime/model loading. The runner
loads each condition independently so the comparison cannot reuse a condition's
configured generator.

## Verdicts

`benefit_observed` requires all integrity checks, at least one successful
recovery, and improvement in at least one predeclared answer-quality metric.

`safe_no_recovery_activated` and `safe_no_measured_benefit` are valid outcomes:
they mean the policy remained safe but the held-out set did not demonstrate the
required benefit.

`baseline_parity_failed`, `integrity_regression`, and `quality_regression`
write their diagnostics and exit non-zero. Investigate those artifacts before
changing any protected setting.
