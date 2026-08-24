# Manual completion checklist

This checklist separates implemented engineering from evidence that still needs
GPUs, independent reviewers, or an upstream maintainer. Check off an item only
when its named artifact exists; a successful smoke test is not a benchmark
result.

## Phase 1 — public repository and recruiter surface

- Confirm the default branch CI is green and the README links resolve.
- Open the deployed portfolio on desktop and mobile and test the AeroRAG-X,
  IntegrityBench, source-code, and CV links in a signed-out browser.
- Confirm the CV PDF contains the same project names and repository URLs.

Done means a recruiter can move from the portfolio to code, methods, limitations,
and measured results without signing in.

## Phase 2 — FSDP and vLLM measurements

Required: one Linux/CUDA host with one GPU for the control, a matched host with
two identical GPUs for FSDP, and enough VRAM to serve the pinned Qwen model.
Pin the repository commit and retain `nvidia-smi`, driver, CUDA, Python, PyTorch,
Transformers, and vLLM versions with the run artifacts.

```bash
python -m pip install -e ".[training]"
python distributed_training/train_fsdp.py --no-fsdp
torchrun --standalone --nproc_per_node=2 distributed_training/train_fsdp.py
python distributed_training/compare_runs.py --help

vllm serve Qwen/Qwen3-4B-Instruct-2507 --enable-prefix-caching
python scripts/benchmark_vllm_serving.py \
  --input data/evaluation/vllm_policy_prefix_v0_1.jsonl \
  --output artifacts/evaluation/vllm_serving_v0_1.json
```

Use identical data, model revision, optimizer settings, seeds, and evaluation
cases for the one- and two-GPU training runs. Exercise checkpoint resume once.
For serving, run concurrency 1, 8, 16, and 32 for normal and shared-prefix
traffic, with a warm-up excluded from measurements. Replace the pending tables
in `reports/fsdp_scaling_v0_1.md` and `reports/vllm_serving_v0_1.md` with the
measured JSON values and attach raw logs. Do not call throughput “scaling”
without the matched one-GPU denominator.

## Phase 3 — IntegrityBench human and low-data study

Required: two independent annotators with moderation-policy literacy and a third
adjudicator. Neither annotator may see the deterministic answer key or the
other annotator's file.

```bash
python scripts/build_annotation_pack.py
cp data/annotation/integritybench_v0_2_blinded.jsonl annotator_a.jsonl
cp data/annotation/integritybench_v0_2_blinded.jsonl annotator_b.jsonl
# Give one copy and docs/annotation-guide.md to each annotator.
python scripts/measure_annotation_agreement.py \
  annotator_a.jsonl annotator_b.jsonl \
  --output artifacts/integritybench_v0_2_agreement.json
```

Adjudicate every disagreement without overwriting either original file. Publish
the blinded pack, annotation guide, agreement summary, adjudication log, label
provenance, and annotator qualifications; redact personal information. For the
low-data study, freeze 8-, 32-, 128-, and full-example training sets before
training, keep the same protected test set for Prompt/RAG/LoRA, use fixed seeds,
and report macro F1, false acceptance, false rejection, escalation, calibration,
citation accuracy, remediation accuracy, and variance. Do not describe v0.1's
deterministic controls as human or model performance.

## Phase 4 — real GRPO comparison

Required: reviewed and licensed aerospace training cases, a protected evaluation
set, and a 16 GB CUDA GPU such as a Kaggle P100.

```bash
python scripts/prepare_grpo_dataset_v0_1.py \
  --training data/training/grpo_grounded_agent_v0_1.jsonl \
  --evaluation data/evaluation/grpo_grounded_eval_v0_1.jsonl
```

Follow `docs/KAGGLE_GRPO.md`: run the five-step smoke test, inspect nonzero
gradients/rewards/tool calls, then run the frozen real dataset. Download the
adapter, checkpoints, logs, archive digest, and `run_receipt.json`. Evaluate
Base, LoRA/SFT, and GRPO on identical protected case IDs and freeze the result:

```bash
python scripts/freeze_grpo_evidence_v0_1.py \
  artifacts/evaluation/policy_observations_v0_1.jsonl
```

Repeat with fixed preregistered seeds if quota permits. Report regressions and
variance. A synthetic fixture, completed training process, or zero-reward run is
not evidence that GRPO improved the system.

## Phase 5 — secondary framework treatments

Required: the same frozen data/model/evaluation contract as Phase 2, Linux/CUDA,
and framework-compatible hardware.

```bash
python -m pip install -e ".[training-deepspeed]"
deepspeed --num_gpus 2 distributed_training/train_deepspeed.py

MEGATRON_LM_ROOT=/path/to/pinned/Megatron-LM \
  python distributed_training/launch_megatron.py
```

Start SGLang and TensorRT-LLM with the model/revision in their checked-in
configs, then send the same evaluation set through the common OpenAI-compatible
provider boundary. Record quality, throughput, latency percentiles, peak memory,
startup time, failures, framework/version, and configuration hashes. Update
`reports/framework_comparison_v0_1.md`; keep unsupported combinations labeled
unsupported rather than converting them into zeroes.

## Phase 6 — upstream contribution

- Reproduce a concrete defect or documentation gap against the current upstream
  default branch; search existing issues and pull requests first.
- Add the smallest regression test, implement the fix, and run the upstream
  project's required format, unit, and integration checks.
- Open a focused pull request that links the reproduction, explains compatibility
  impact, and discloses any AI assistance required by the project policy.
- Respond to review and update this repository only with the real PR URL and its
  factual status: opened, merged, or declined.

An accepted contribution depends on an external maintainer. Do not create a
token change merely to obtain a PR badge, and do not say “upstream contribution
completed” until a relevant patch has been merged.

## Final publication gate

- Run the full repository test, lint, type-check, and Docker smoke suites.
- Regenerate every checked-in report from raw artifacts and ensure `git diff` is
  empty afterward.
- Have a second person audit every numeric portfolio/CV/README claim against the
  named artifact and commit.
- Publish raw measurements and limitations before promoting headline metrics.
