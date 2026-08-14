#!/usr/bin/env python3
"""Aggregate held-out Base, LoRA/SFT, and GRPO policy observations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.evaluation.grpo_ablation import (
    PolicyEvaluationObservation,
    build_ablation,
)


def load(path: Path) -> list[PolicyEvaluationObservation]:
    rows: list[PolicyEvaluationObservation] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(PolicyEvaluationObservation.model_validate_json(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("observations", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/evaluation/grpo_agent_ablation_v0_1.json"),
    )
    args = parser.parse_args()

    result = build_ablation(load(args.observations))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
