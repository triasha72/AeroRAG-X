"""Leakage guards for post-training and protected evaluation sets."""

from collections.abc import Iterable


def validate_disjoint_case_ids(
    training_case_ids: Iterable[str],
    evaluation_case_ids: Iterable[str],
) -> None:
    """Reject any case-ID overlap between post-training and frozen evaluation."""

    training = set(training_case_ids)
    evaluation = set(evaluation_case_ids)
    overlap = sorted(training & evaluation)
    if overlap:
        raise ValueError(f"GRPO training/evaluation case IDs must be disjoint: {overlap}")
