#!/usr/bin/env python3
"""Validate or execute the bounded AeroRAG-X GRPO experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from aeroragx.training.grpo.config import GRPOExperimentConfig
from aeroragx.training.grpo.io import load_grounded_training_cases
from aeroragx.training.grpo.trainer import run_grpo_training


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        required=True,
        help="Versioned GRPO training-case JSONL.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/grpo_grounded_agent_v0_1.yaml"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/models/grpo_grounded_agent_v0_1"),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually start GRPO training. Without this flag, validate only.",
    )
    args = parser.parse_args()

    raw = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    raw.pop("version", None)
    config = GRPOExperimentConfig.model_validate(raw)
    cases = load_grounded_training_cases(args.cases)

    print(
        json.dumps(
            {
                "model_id": config.model_id,
                "case_count": len(cases),
                "max_steps": config.max_steps,
                "num_generations": config.num_generations,
                "execute": args.execute,
            },
            indent=2,
            sort_keys=True,
        )
    )

    if not args.execute:
        print("Validation-only run complete. Add --execute on a suitable training host.")
        return

    run_grpo_training(
        cases=cases,
        config=config,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
