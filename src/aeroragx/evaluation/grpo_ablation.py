"""Held-out Base vs LoRA/SFT vs GRPO ablation metrics."""

from __future__ import annotations

from statistics import median
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModelVariant = Literal["base", "lora_sft", "grpo"]


class PolicyEvaluationObservation(BaseModel):
    """One held-out case result for one model variant."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=1)
    variant: ModelVariant
    task_success: bool
    refusal_correct: bool
    citation_valid: bool
    evidence_supported: bool
    tool_selection_correct: bool
    tool_calls: int = Field(ge=0)
    structured_output_valid: bool
    latency_ms: float = Field(ge=0.0)


class PolicyEvaluationMetrics(BaseModel):
    """Aggregate held-out engineering metrics for one variant."""

    model_config = ConfigDict(extra="forbid")

    case_count: int = Field(ge=1)
    task_success_rate: float = Field(ge=0.0, le=1.0)
    refusal_accuracy: float = Field(ge=0.0, le=1.0)
    citation_validity_rate: float = Field(ge=0.0, le=1.0)
    evidence_support_rate: float = Field(ge=0.0, le=1.0)
    tool_selection_accuracy: float = Field(ge=0.0, le=1.0)
    structured_output_rate: float = Field(ge=0.0, le=1.0)
    mean_tool_calls: float = Field(ge=0.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)


class PolicyAblationResult(BaseModel):
    """Metrics for all three controlled policy variants."""

    model_config = ConfigDict(extra="forbid")

    base: PolicyEvaluationMetrics
    lora_sft: PolicyEvaluationMetrics
    grpo: PolicyEvaluationMetrics


def summarize_variant(
    observations: list[PolicyEvaluationObservation],
) -> PolicyEvaluationMetrics:
    if not observations:
        raise ValueError("Variant metrics require at least one observation.")

    count = len(observations)
    latencies = sorted(item.latency_ms for item in observations)
    p95_index = max(round(0.95 * (count - 1)), 0)

    return PolicyEvaluationMetrics(
        case_count=count,
        task_success_rate=sum(item.task_success for item in observations) / count,
        refusal_accuracy=sum(item.refusal_correct for item in observations) / count,
        citation_validity_rate=sum(item.citation_valid for item in observations) / count,
        evidence_support_rate=sum(item.evidence_supported for item in observations) / count,
        tool_selection_accuracy=(sum(item.tool_selection_correct for item in observations) / count),
        structured_output_rate=(sum(item.structured_output_valid for item in observations) / count),
        mean_tool_calls=sum(item.tool_calls for item in observations) / count,
        p50_latency_ms=float(median(latencies)),
        p95_latency_ms=latencies[p95_index],
    )


def build_ablation(
    observations: list[PolicyEvaluationObservation],
) -> PolicyAblationResult:
    by_variant: dict[ModelVariant, list[PolicyEvaluationObservation]] = {
        "base": [],
        "lora_sft": [],
        "grpo": [],
    }
    case_sets: dict[ModelVariant, set[str]] = {
        "base": set(),
        "lora_sft": set(),
        "grpo": set(),
    }

    for item in observations:
        by_variant[item.variant].append(item)
        case_sets[item.variant].add(item.case_id)

    if not all(by_variant.values()):
        raise ValueError("Ablation requires base, lora_sft, and grpo observations.")

    if not (case_sets["base"] == case_sets["lora_sft"] == case_sets["grpo"]):
        raise ValueError("All ablation variants must evaluate exactly the same held-out case IDs.")

    return PolicyAblationResult(
        base=summarize_variant(by_variant["base"]),
        lora_sft=summarize_variant(by_variant["lora_sft"]),
        grpo=summarize_variant(by_variant["grpo"]),
    )
