#!/usr/bin/env python3
"""Validate or execute the bounded AeroRAG-X GRPO experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import yaml

from aeroragx.training.grpo.config import GRPOExperimentConfig
from aeroragx.training.grpo.io import load_grounded_training_cases
from aeroragx.training.grpo.trainer import latest_checkpoint, run_grpo_training


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        required=True,
        help="Versioned GRPO training-case JSONL.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the latest checkpoint under --output-dir when one exists.",
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

    started_at = datetime.now(UTC)
    checkpoint = latest_checkpoint(args.output_dir) if args.resume else None
    final_checkpoint = run_grpo_training(
        cases=cases,
        config=config,
        output_dir=args.output_dir,
        resume_from_checkpoint=checkpoint,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "model_id": config.model_id,
        "config_sha256": sha256(args.config),
        "cases_sha256": sha256(args.cases),
        "case_count": len(cases),
        "max_steps": config.max_steps,
        "resumed_from": str(checkpoint) if checkpoint else None,
        "final_checkpoint": str(final_checkpoint) if final_checkpoint else None,
    }
    (args.output_dir / "run_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
