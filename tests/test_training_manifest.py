"""Tests for LoRA dataset-generation receipts."""

from __future__ import annotations

from pathlib import Path

import pytest

from aeroragx.training.manifest import (
    DatasetGenerationReceipt,
    PlanGenerationReceipt,
    load_dataset_generation_receipt,
    make_dataset_generation_receipt,
    summarize_generation_receipts,
    write_dataset_generation_receipt,
)


def make_accepted_receipt(
    *,
    plan_id: str = "plan_0001",
    example_type: str = "ordinary",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cost: float = 0.001,
) -> PlanGenerationReceipt:
    """Create one accepted generation receipt."""

    return PlanGenerationReceipt(
        plan_id=plan_id,
        example_type=example_type,
        status="accepted",
        example_id=f"train_{plan_id}",
        question_attempts=1,
        verification_attempts=0,
        answer_attempts=1,
        question_request_ids=[f"question_{plan_id}"],
        verification_request_ids=[],
        answer_request_ids=[f"answer_{plan_id}"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=(input_tokens + output_tokens),
        estimated_cost_usd=cost,
        telemetry_complete=True,
        rejection_reason=None,
    )


def make_rejected_receipt() -> PlanGenerationReceipt:
    """Create one rejected generation receipt."""

    return PlanGenerationReceipt(
        plan_id="plan_0002",
        example_type="synthesis",
        status="rejected",
        example_id=None,
        question_attempts=2,
        verification_attempts=0,
        answer_attempts=1,
        question_request_ids=[
            "question_plan_0002_a",
            "question_plan_0002_b",
        ],
        verification_request_ids=[],
        answer_request_ids=["answer_plan_0002"],
        input_tokens=200,
        output_tokens=40,
        total_tokens=240,
        estimated_cost_usd=0.002,
        telemetry_complete=True,
        rejection_reason=("Synthesis output did not satisfy multi-evidence requirements."),
    )


def make_failed_receipt() -> PlanGenerationReceipt:
    """Create one failed generation receipt."""

    return PlanGenerationReceipt(
        plan_id="plan_0003",
        example_type="refusal",
        status="failed",
        example_id=None,
        question_attempts=1,
        verification_attempts=1,
        answer_attempts=0,
        question_request_ids=["question_plan_0003"],
        verification_request_ids=["verification_plan_0003"],
        answer_request_ids=[],
        input_tokens=50,
        output_tokens=10,
        total_tokens=60,
        estimated_cost_usd=0.0005,
        telemetry_complete=True,
        rejection_reason=("Teacher transport failed."),
    )


def make_generation_receipt(
    records: list[PlanGenerationReceipt],
) -> DatasetGenerationReceipt:
    """Create an aggregate receipt fixture."""

    return make_dataset_generation_receipt(
        version="0.1",
        example_plan_path=("data/example_plan.json"),
        example_plan_sha256=("a" * 64),
        teacher_config_path=("configs/teacher.yaml"),
        teacher_config_sha256=("b" * 64),
        dataset_config_path=("configs/dataset.yaml"),
        dataset_config_sha256=("c" * 64),
        planned_example_count=3,
        records=records,
    )


def test_accepted_receipt_requires_example_id() -> None:
    with pytest.raises(
        ValueError,
        match="require example_id",
    ):
        PlanGenerationReceipt(
            plan_id="plan_0001",
            example_type="ordinary",
            status="accepted",
            example_id=None,
            question_attempts=1,
            verification_attempts=0,
            answer_attempts=1,
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            estimated_cost_usd=0.0,
            telemetry_complete=True,
        )


def test_unsuccessful_receipt_requires_reason() -> None:
    with pytest.raises(
        ValueError,
        match="require rejection_reason",
    ):
        PlanGenerationReceipt(
            plan_id="plan_0001",
            example_type="ordinary",
            status="failed",
            example_id=None,
            question_attempts=0,
            verification_attempts=0,
            answer_attempts=0,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            telemetry_complete=False,
            rejection_reason=None,
        )


def test_total_tokens_are_validated() -> None:
    with pytest.raises(
        ValueError,
        match="total_tokens",
    ):
        PlanGenerationReceipt(
            plan_id="plan_0001",
            example_type="ordinary",
            status="accepted",
            example_id="train_plan_0001",
            question_attempts=1,
            verification_attempts=0,
            answer_attempts=1,
            input_tokens=10,
            output_tokens=5,
            total_tokens=100,
            estimated_cost_usd=0.0,
            telemetry_complete=True,
        )


def test_summary_aggregates_status_counts() -> None:
    summary = summarize_generation_receipts(
        [
            make_accepted_receipt(),
            make_rejected_receipt(),
            make_failed_receipt(),
        ]
    )

    assert summary.record_count == 3

    assert summary.accepted_count == 1

    assert summary.rejected_count == 1

    assert summary.failed_count == 1


def test_summary_aggregates_tokens() -> None:
    summary = summarize_generation_receipts(
        [
            make_accepted_receipt(),
            make_rejected_receipt(),
            make_failed_receipt(),
        ]
    )

    assert summary.total_input_tokens == 350

    assert summary.total_output_tokens == 70

    assert summary.total_tokens == 420


def test_summary_aggregates_cost() -> None:
    summary = summarize_generation_receipts(
        [
            make_accepted_receipt(),
            make_rejected_receipt(),
            make_failed_receipt(),
        ]
    )

    assert summary.total_estimated_cost_usd == pytest.approx(0.0035)


def test_summary_aggregates_accepted_types() -> None:
    summary = summarize_generation_receipts(
        [
            make_accepted_receipt(
                plan_id="plan_0001",
                example_type="ordinary",
            ),
            make_accepted_receipt(
                plan_id="plan_0002",
                example_type="synthesis",
            ),
            make_accepted_receipt(
                plan_id="plan_0003",
                example_type="refusal",
            ),
        ]
    )

    assert summary.ordinary_accepted_count == 1

    assert summary.synthesis_accepted_count == 1

    assert summary.refusal_accepted_count == 1


def test_generation_receipt_sorts_records() -> None:
    receipt = make_generation_receipt(
        [
            make_failed_receipt(),
            make_accepted_receipt(),
            make_rejected_receipt(),
        ]
    )

    assert [record.plan_id for record in receipt.records] == [
        "plan_0001",
        "plan_0002",
        "plan_0003",
    ]


def test_complete_receipt_reports_complete() -> None:
    receipt = make_generation_receipt(
        [
            make_accepted_receipt(
                plan_id="plan_0001",
                example_type="ordinary",
            ),
            make_accepted_receipt(
                plan_id="plan_0002",
                example_type="synthesis",
            ),
            make_accepted_receipt(
                plan_id="plan_0003",
                example_type="refusal",
            ),
        ]
    )

    assert receipt.is_complete

    assert receipt.accepted_plan_ids == {
        "plan_0001",
        "plan_0002",
        "plan_0003",
    }


def test_receipt_with_failure_is_incomplete() -> None:
    receipt = make_generation_receipt(
        [
            make_accepted_receipt(),
            make_rejected_receipt(),
            make_failed_receipt(),
        ]
    )

    assert not receipt.is_complete


def test_receipt_round_trip(
    tmp_path: Path,
) -> None:
    receipt = make_generation_receipt(
        [
            make_accepted_receipt(),
            make_rejected_receipt(),
            make_failed_receipt(),
        ]
    )

    output = tmp_path / "receipt.json"

    write_dataset_generation_receipt(
        output,
        receipt,
    )

    loaded = load_dataset_generation_receipt(output)

    assert loaded == receipt


def test_receipt_serialization_is_deterministic(
    tmp_path: Path,
) -> None:
    receipt = make_generation_receipt(
        [
            make_accepted_receipt(),
            make_rejected_receipt(),
            make_failed_receipt(),
        ]
    )

    first = tmp_path / "first.json"

    second = tmp_path / "second.json"

    write_dataset_generation_receipt(
        first,
        receipt,
    )

    write_dataset_generation_receipt(
        second,
        receipt,
    )

    assert first.read_bytes() == second.read_bytes()
