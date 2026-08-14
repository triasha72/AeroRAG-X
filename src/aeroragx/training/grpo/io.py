"""I/O helpers for grounded-agent GRPO training cases."""

from pathlib import Path

from aeroragx.training.grpo.dataset import GroundedAgentTrainingCase


def load_grounded_training_cases(
    path: Path,
) -> list[GroundedAgentTrainingCase]:
    cases: list[GroundedAgentTrainingCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(GroundedAgentTrainingCase.model_validate_json(line))
    if not cases:
        raise ValueError("Training case file must contain at least one case.")
    return cases
