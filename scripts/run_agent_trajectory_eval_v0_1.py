#!/usr/bin/env python3
"""Evaluate previously recorded agent run observations from JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.evaluation.agent_metrics import evaluate_agent_trajectories
from aeroragx.evaluation.agent_trajectory import AgentTrajectoryObservation


def load_jsonl(path: Path) -> list[AgentTrajectoryObservation]:
    observations: list[AgentTrajectoryObservation] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            observations.append(AgentTrajectoryObservation.model_validate_json(line))
    return observations


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("observations", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/evaluation/agent_trajectory_metrics_v0_1.json"),
    )
    args = parser.parse_args()

    metrics = evaluate_agent_trajectories(load_jsonl(args.observations))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(metrics.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
