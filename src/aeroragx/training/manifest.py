"""Dataset-generation configuration and auditable generation receipts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from aeroragx.training.builder import (
    ExampleBuildResult,
)
from aeroragx.training.planning import (
    ExamplePlanType,
    PlannedExample,
)

type GenerationStatus = Literal[
    "accepted",
    "rejected",
    "failed",
]


class DatasetInputConfig(BaseModel):
    """Immutable inputs required to construct the training dataset."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    chunks: str = Field(
        min_length=1,
    )

    example_plan: str = Field(
        min_length=1,
    )

    source_selection: str = Field(
        min_length=1,
    )

    protected_manifest: str = Field(
        min_length=1,
    )

    protected_queries: str = Field(
        min_length=1,
    )

    protected_generation_report: str = Field(
        min_length=1,
    )


class DatasetTeacherConfig(BaseModel):
    """Teacher configuration path."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    config: str = Field(
        min_length=1,
    )


class DatasetWorkingConfig(BaseModel):
    """Checkpoint artifacts used during resumable generation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    examples: str = Field(
        min_length=1,
    )

    receipt: str = Field(
        min_length=1,
    )


class DatasetOutputConfig(BaseModel):
    """Permanent dataset artifacts."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    dataset: str = Field(
        min_length=1,
    )

    manifest: str = Field(
        min_length=1,
    )

    train: str = Field(
        min_length=1,
    )

    dev: str = Field(
        min_length=1,
    )

    audit_report: str = Field(
        min_length=1,
    )


class DatasetExpectedConfig(BaseModel):
    """Expected frozen example-plan composition."""

    model_config = ConfigDict(
        extra="forbid",
    )

    total: int = Field(
        ge=1,
    )

    ordinary: int = Field(
        ge=0,
    )

    synthesis: int = Field(
        ge=0,
    )

    refusal: int = Field(
        ge=0,
    )

    @model_validator(mode="after")
    def validate_expected_total(
        self,
    ) -> Self:
        """Require category counts to sum to the frozen total."""

        observed = self.ordinary + self.synthesis + self.refusal

        if observed != self.total:
            raise ValueError(
                "Expected ordinary, synthesis, and refusal counts must sum to expected total."
            )

        return self


class DatasetSplitConfig(BaseModel):
    """Document-aware train/dev split configuration."""

    model_config = ConfigDict(
        extra="forbid",
    )

    dev_fraction: float = Field(
        ge=0.0,
        le=1.0,
    )

    seed: int


class DatasetTrainingConfig(BaseModel):
    """Future training-format limits audited before LoRA training."""

    model_config = ConfigDict(
        extra="forbid",
    )

    max_sequence_tokens: int = Field(
        ge=1,
    )


class DatasetBuildConfig(BaseModel):
    """Complete v0.1 dataset-generation configuration."""

    model_config = ConfigDict(
        extra="forbid",
    )

    version: str = Field(
        min_length=1,
    )

    inputs: DatasetInputConfig

    teacher: DatasetTeacherConfig

    working: DatasetWorkingConfig

    outputs: DatasetOutputConfig

    expected: DatasetExpectedConfig

    split: DatasetSplitConfig

    training: DatasetTrainingConfig


class PlanGenerationReceipt(BaseModel):
    """Auditable result of attempting one frozen example plan."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    plan_id: str = Field(
        min_length=1,
    )

    example_type: ExamplePlanType

    status: GenerationStatus

    example_id: str | None = None

    question_attempts: int = Field(
        ge=0,
    )

    verification_attempts: int = Field(
        ge=0,
    )

    answer_attempts: int = Field(
        ge=0,
    )

    question_request_ids: list[str] = Field(
        default_factory=list,
    )

    verification_request_ids: list[str] = Field(
        default_factory=list,
    )

    answer_request_ids: list[str] = Field(
        default_factory=list,
    )

    input_tokens: int = Field(
        ge=0,
    )

    output_tokens: int = Field(
        ge=0,
    )

    total_tokens: int = Field(
        ge=0,
    )

    estimated_cost_usd: float = Field(
        ge=0.0,
    )

    telemetry_complete: bool

    rejection_reason: str | None = None

    @model_validator(mode="after")
    def validate_receipt_state(
        self,
    ) -> Self:
        """Ensure accepted and unsuccessful states remain distinct."""

        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens + output_tokens.")

        if len(self.question_request_ids) != len(set(self.question_request_ids)):
            raise ValueError("question_request_ids must be unique.")

        if len(self.verification_request_ids) != len(set(self.verification_request_ids)):
            raise ValueError("verification_request_ids must be unique.")

        if len(self.answer_request_ids) != len(set(self.answer_request_ids)):
            raise ValueError("answer_request_ids must be unique.")

        if self.status == "accepted":
            if self.example_id is None or not self.example_id.strip():
                raise ValueError("Accepted generation receipts require example_id.")

            if self.rejection_reason is not None:
                raise ValueError("Accepted generation receipts must not contain rejection_reason.")

        else:
            if self.example_id is not None:
                raise ValueError(
                    "Rejected or failed generation receipts must not contain example_id."
                )

            if self.rejection_reason is None or not self.rejection_reason.strip():
                raise ValueError("Rejected or failed generation receipts require rejection_reason.")

        return self


class GenerationSummary(BaseModel):
    """Aggregate generation metrics derived from receipt records."""

    model_config = ConfigDict(
        extra="forbid",
    )

    record_count: int = Field(
        ge=0,
    )

    accepted_count: int = Field(
        ge=0,
    )

    rejected_count: int = Field(
        ge=0,
    )

    failed_count: int = Field(
        ge=0,
    )

    ordinary_accepted_count: int = Field(
        ge=0,
    )

    synthesis_accepted_count: int = Field(
        ge=0,
    )

    refusal_accepted_count: int = Field(
        ge=0,
    )

    total_question_attempts: int = Field(
        ge=0,
    )

    total_verification_attempts: int = Field(
        ge=0,
    )

    total_answer_attempts: int = Field(
        ge=0,
    )

    total_input_tokens: int = Field(
        ge=0,
    )

    total_output_tokens: int = Field(
        ge=0,
    )

    total_tokens: int = Field(
        ge=0,
    )

    total_estimated_cost_usd: float = Field(
        ge=0.0,
    )

    telemetry_complete: bool


class DatasetGenerationReceipt(BaseModel):
    """Resumable generation receipt for the complete frozen plan."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(
        min_length=1,
    )

    example_plan_path: str = Field(
        min_length=1,
    )

    example_plan_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    teacher_config_path: str = Field(
        min_length=1,
    )

    teacher_config_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    dataset_config_path: str = Field(
        min_length=1,
    )

    dataset_config_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    planned_example_count: int = Field(
        ge=1,
    )

    summary: GenerationSummary

    records: list[PlanGenerationReceipt] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_generation_receipt(
        self,
    ) -> Self:
        """Validate record uniqueness, ordering, and derived summary."""

        plan_ids = [record.plan_id for record in self.records]

        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("Generation receipt contains duplicate plan IDs.")

        if plan_ids != sorted(plan_ids):
            raise ValueError("Generation receipt records must be sorted by plan_id.")

        expected_summary = summarize_generation_receipts(self.records)

        if self.summary != expected_summary:
            raise ValueError("Generation receipt summary does not match its plan records.")

        if len(self.records) > self.planned_example_count:
            raise ValueError("Generation receipt contains more records than the frozen plan.")

        return self

    @property
    def accepted_plan_ids(
        self,
    ) -> set[str]:
        """Return all successfully completed plan IDs."""

        return {record.plan_id for record in self.records if record.status == "accepted"}

    @property
    def is_complete(
        self,
    ) -> bool:
        """Return whether every frozen plan is accepted."""

        return (
            self.summary.accepted_count == self.planned_example_count
            and self.summary.rejected_count == 0
            and self.summary.failed_count == 0
        )


def load_dataset_build_config(
    path: Path,
) -> DatasetBuildConfig:
    """Load and validate dataset-generation YAML."""

    try:
        raw_value = yaml.safe_load(path.read_text(encoding="utf-8"))

    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid dataset-build YAML in {path}.") from exc

    if not isinstance(
        raw_value,
        dict,
    ):
        raise ValueError("Dataset-build configuration must contain a YAML mapping.")

    try:
        return DatasetBuildConfig.model_validate(raw_value)

    except ValidationError as exc:
        raise ValueError(f"Invalid dataset-build config {path}.") from exc


def summarize_generation_receipts(
    records: list[PlanGenerationReceipt],
) -> GenerationSummary:
    """Aggregate auditable counters over generation records."""

    accepted = [record for record in records if record.status == "accepted"]

    return GenerationSummary(
        record_count=len(records),
        accepted_count=len(accepted),
        rejected_count=sum(1 for record in records if record.status == "rejected"),
        failed_count=sum(1 for record in records if record.status == "failed"),
        ordinary_accepted_count=sum(1 for record in accepted if record.example_type == "ordinary"),
        synthesis_accepted_count=sum(
            1 for record in accepted if record.example_type == "synthesis"
        ),
        refusal_accepted_count=sum(1 for record in accepted if record.example_type == "refusal"),
        total_question_attempts=sum(record.question_attempts for record in records),
        total_verification_attempts=sum(record.verification_attempts for record in records),
        total_answer_attempts=sum(record.answer_attempts for record in records),
        total_input_tokens=sum(record.input_tokens for record in records),
        total_output_tokens=sum(record.output_tokens for record in records),
        total_tokens=sum(record.total_tokens for record in records),
        total_estimated_cost_usd=sum(record.estimated_cost_usd for record in records),
        telemetry_complete=all(record.telemetry_complete for record in records),
    )


def receipt_from_build_result(
    result: ExampleBuildResult,
) -> PlanGenerationReceipt:
    """Create one accepted receipt from a validated builder result."""

    teacher_telemetry = [
        *result.question_telemetry,
        *result.verification_telemetry,
    ]

    input_tokens = 0
    output_tokens = 0
    estimated_cost = 0.0
    telemetry_complete = True

    for telemetry in teacher_telemetry:
        if (
            telemetry.usage is None
            or telemetry.usage.input_tokens is None
            or telemetry.usage.output_tokens is None
        ):
            telemetry_complete = False

        else:
            input_tokens += telemetry.usage.input_tokens

            output_tokens += telemetry.usage.output_tokens

        if telemetry.estimated_cost_usd is None:
            telemetry_complete = False

        else:
            estimated_cost += telemetry.estimated_cost_usd

    answer_attempts = 0
    answer_request_ids: list[str] = []

    if result.answer_telemetry is not None:
        answer_attempts = result.answer_telemetry.attempts

        if result.answer_telemetry.request_id is not None:
            answer_request_ids.append(result.answer_telemetry.request_id)

        usage = result.answer_telemetry.usage

        if usage is None or usage.input_tokens is None or usage.output_tokens is None:
            telemetry_complete = False

        else:
            input_tokens += usage.input_tokens

            output_tokens += usage.output_tokens

        if result.answer_telemetry.estimated_cost_usd is None:
            telemetry_complete = False

        else:
            estimated_cost += result.answer_telemetry.estimated_cost_usd

    return PlanGenerationReceipt(
        plan_id=result.plan_id,
        example_type=(result.example_type),
        status="accepted",
        example_id=(result.example.example_id),
        question_attempts=(result.question_attempts),
        verification_attempts=len(result.verification_telemetry),
        answer_attempts=(answer_attempts),
        question_request_ids=[
            telemetry.request_id
            for telemetry in result.question_telemetry
            if telemetry.request_id is not None
        ],
        verification_request_ids=[
            telemetry.request_id
            for telemetry in result.verification_telemetry
            if telemetry.request_id is not None
        ],
        answer_request_ids=(answer_request_ids),
        input_tokens=(input_tokens),
        output_tokens=(output_tokens),
        total_tokens=(input_tokens + output_tokens),
        estimated_cost_usd=(estimated_cost),
        telemetry_complete=(telemetry_complete),
        rejection_reason=None,
    )


def unsuccessful_plan_receipt(
    plan: PlannedExample,
    *,
    status: Literal[
        "rejected",
        "failed",
    ],
    reason: str,
) -> PlanGenerationReceipt:
    """Create a failure/rejection receipt when no build result exists."""

    normalized_reason = " ".join(reason.split())

    if not normalized_reason:
        raise ValueError("Unsuccessful generation receipt requires a nonblank reason.")

    return PlanGenerationReceipt(
        plan_id=plan.plan_id,
        example_type=(plan.example_type),
        status=status,
        example_id=None,
        question_attempts=0,
        verification_attempts=0,
        answer_attempts=0,
        question_request_ids=[],
        verification_request_ids=[],
        answer_request_ids=[],
        input_tokens=0,
        output_tokens=0,
        total_tokens=0,
        estimated_cost_usd=0.0,
        telemetry_complete=False,
        rejection_reason=(normalized_reason),
    )


def make_dataset_generation_receipt(
    *,
    version: str,
    example_plan_path: str,
    example_plan_sha256: str,
    teacher_config_path: str,
    teacher_config_sha256: str,
    dataset_config_path: str,
    dataset_config_sha256: str,
    planned_example_count: int,
    records: list[PlanGenerationReceipt],
) -> DatasetGenerationReceipt:
    """Construct a deterministically ordered aggregate receipt."""

    ordered_records = sorted(
        (record.model_copy(deep=True) for record in records),
        key=lambda record: record.plan_id,
    )

    return DatasetGenerationReceipt(
        version=version,
        example_plan_path=(example_plan_path),
        example_plan_sha256=(example_plan_sha256),
        teacher_config_path=(teacher_config_path),
        teacher_config_sha256=(teacher_config_sha256),
        dataset_config_path=(dataset_config_path),
        dataset_config_sha256=(dataset_config_sha256),
        planned_example_count=(planned_example_count),
        summary=(summarize_generation_receipts(ordered_records)),
        records=(ordered_records),
    )


def load_dataset_generation_receipt(
    path: Path,
) -> DatasetGenerationReceipt:
    """Load and validate one resumable generation receipt."""

    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))

    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid generation receipt JSON in {path}.") from exc

    try:
        return DatasetGenerationReceipt.model_validate(raw_value)

    except ValidationError as exc:
        raise ValueError(f"Invalid generation receipt {path}.") from exc


def write_dataset_generation_receipt(
    path: Path,
    receipt: DatasetGenerationReceipt,
) -> None:
    """Write a deterministic generation receipt."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            receipt.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
