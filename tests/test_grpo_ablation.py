"""Tests for controlled Base vs LoRA/SFT vs GRPO ablation."""

import pytest

from aeroragx.evaluation.grpo_ablation import (
    PolicyEvaluationObservation,
    build_ablation,
)


def row(variant: str, case_id: str = "c1") -> PolicyEvaluationObservation:
    return PolicyEvaluationObservation.model_validate(
        {
            "case_id": case_id,
            "variant": variant,
            "task_success": True,
            "refusal_correct": True,
            "citation_valid": True,
            "evidence_supported": True,
            "tool_selection_correct": True,
            "tool_calls": 2,
            "structured_output_valid": True,
            "latency_ms": 10.0,
        }
    )


def test_ablation_requires_same_case_ids() -> None:
    with pytest.raises(ValueError, match="same held-out case IDs"):
        build_ablation(
            [
                row("base", "c1"),
                row("lora_sft", "c1"),
                row("grpo", "different"),
            ]
        )


def test_ablation_reports_all_variants() -> None:
    result = build_ablation(
        [row("base"), row("lora_sft"), row("grpo")]
    )
    assert result.base.task_success_rate == 1.0
    assert result.grpo.case_count == 1
