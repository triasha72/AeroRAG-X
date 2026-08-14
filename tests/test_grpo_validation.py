"""Tests for post-training/evaluation leakage guards."""

import pytest

from aeroragx.training.grpo.validation import validate_disjoint_case_ids


def test_case_overlap_is_rejected() -> None:
    with pytest.raises(ValueError, match="disjoint"):
        validate_disjoint_case_ids(["train-1", "shared"], ["eval-1", "shared"])
