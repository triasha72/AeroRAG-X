# Produce a real GRPO result

A real result requires reviewed aerospace cases, an executed GPU run, and a
controlled held-out comparison. The repository automates validation, hashing,
training, checkpoint recovery, aggregation, and report generation; humans must
still curate the domain cases and inspect the judgments.

## 1. Prepare and freeze the data

Create training and protected-evaluation JSONL files using the
`GroundedAgentTrainingCase` contract. Keep the protected file private until all
training choices are fixed. Then run:

```bash
python scripts/prepare_grpo_dataset_v0_1.py \
  --training data/training/grpo_grounded_agent_v0_1.jsonl \
  --evaluation data/evaluation/grpo_grounded_eval_v0_1.jsonl
```

This rejects duplicate IDs, internally inconsistent cases, missing citations,
and near-duplicate queries across splits. It writes a manifest containing case
counts and SHA-256 identities. A domain reviewer must still confirm technical
correctness and source licensing.

## 2. Execute training on Kaggle

Follow `docs/KAGGLE_GRPO.md`, attach the validated private training file, and
use `configs/grpo_kaggle_p100_v0_1.yaml`. Retain the final adapter, checkpoint,
logs, archive digest, and `run_receipt.json`. Repeat with fixed seeds when GPU
quota allows; do not tune against the protected cases.

## 3. Record the held-out comparison

Run Base, the existing LoRA/SFT adapter, and the new GRPO adapter on precisely
the same protected case IDs. Record one `PolicyEvaluationObservation` per case
and variant, including `model_id`, `model_revision`, `seed`, and the adapter
SHA-256 for adapted variants. A reviewer should verify answer correctness,
evidence support, citations, refusals, and required tool behavior.

## 4. Freeze the measured evidence

```bash
python scripts/freeze_grpo_evidence_v0_1.py \
  artifacts/evaluation/policy_observations_v0_1.jsonl
```

The command enforces identical case IDs across all variants and refuses to
label the report measured when reproducibility metadata is missing. It writes
the aggregate JSON and a Markdown report tied to the observation-file hash.
The checked-in observation template is accepted only with `--allow-synthetic`,
and the resulting report is visibly labeled as a non-evidence fixture.

The result should be described as an improvement only when the protected
metrics support that conclusion. Regressions and run-to-run variance belong in
the report as well.
