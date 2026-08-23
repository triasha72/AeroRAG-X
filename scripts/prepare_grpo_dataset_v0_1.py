#!/usr/bin/env python3
"""Validate real GRPO splits and freeze a reproducible dataset manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.training.grpo.io import load_grounded_training_cases
from aeroragx.training.grpo.validation import build_dataset_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/evaluation/grpo_dataset_manifest_v0_1.json"),
    )
    parser.add_argument("--near-duplicate-threshold", type=float, default=0.92)
    args = parser.parse_args()

    manifest = build_dataset_manifest(
        training_path=args.training,
        training_cases=load_grounded_training_cases(args.training),
        evaluation_path=args.evaluation,
        evaluation_cases=load_grounded_training_cases(args.evaluation),
        near_duplicate_threshold=args.near_duplicate_threshold,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
