"""Validated reporting utilities for local edge-runtime benchmarks."""

from __future__ import annotations

import json
import math
import platform
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

type BenchmarkDevice = Literal["auto", "cpu", "mps", "cuda"]
type BenchmarkDtype = Literal["auto", "float32", "float16", "bfloat16"]


class EdgeRuntimeBenchmarkCase(BaseModel):
    """One reproducible local-inference benchmark condition."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    device: BenchmarkDevice
    dtype: BenchmarkDtype
    adapter_path: Path | None = None


class EdgeRuntimeBenchmarkConfig(BaseModel):
    """Configuration for a bounded local-runtime benchmark."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: str = "0.1"
    model_name: str = Field(min_length=1)
    template_runtime_config: Path
    warmup_iterations: int = Field(ge=0, le=10)
    measured_iterations: int = Field(ge=1, le=20)
    timeout_seconds: float = Field(gt=0.0, le=600.0)
    max_input_tokens: int = Field(ge=1)
    max_new_tokens: int = Field(ge=1)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    cases: list[EdgeRuntimeBenchmarkCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_cases_and_budget(self) -> EdgeRuntimeBenchmarkConfig:
        """Ensure cases are uniquely named and token budgets are valid."""

        case_names = [case.name for case in self.cases]

        if len(case_names) != len(set(case_names)):
            raise ValueError("Benchmark case names must be unique.")

        if self.max_input_tokens + self.max_new_tokens > 32_768:
            raise ValueError("max_input_tokens + max_new_tokens must not exceed 32768.")

        return self


class EdgeRuntimeBenchmarkSample(BaseModel):
    """One measured completion after warm-up."""

    model_config = ConfigDict(extra="forbid")

    case_name: str = Field(min_length=1)
    iteration: int = Field(ge=1)
    latency_ms: float = Field(ge=0.0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @property
    def output_tokens_per_second(self) -> float | None:
        """Return output throughput when latency and output are both positive."""

        if self.latency_ms <= 0.0 or self.output_tokens <= 0:
            return None

        return self.output_tokens / (self.latency_ms / 1000.0)


class EdgeRuntimeBenchmarkCaseSummary(BaseModel):
    """Aggregated latency and throughput statistics for one benchmark case."""

    model_config = ConfigDict(extra="forbid")

    case_name: str = Field(min_length=1)
    device: BenchmarkDevice
    dtype: BenchmarkDtype
    adapter_path: str | None = None
    sample_count: int = Field(ge=1)
    mean_latency_ms: float = Field(ge=0.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)
    output_tokens_per_second: float | None = Field(default=None, ge=0.0)


class EdgeRuntimeBenchmarkReport(BaseModel):
    """Versioned report for a local edge-runtime benchmark."""

    model_config = ConfigDict(extra="forbid")

    version: str
    model_name: str
    platform: str
    python_version: str
    torch_version: str
    warmup_iterations: int = Field(ge=0)
    measured_iterations: int = Field(ge=1)
    case_summaries: list[EdgeRuntimeBenchmarkCaseSummary] = Field(min_length=1)
    samples: list[EdgeRuntimeBenchmarkSample] = Field(min_length=1)


def load_edge_runtime_benchmark_config(path: Path) -> EdgeRuntimeBenchmarkConfig:
    """Load and validate one edge-runtime benchmark YAML configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Edge-runtime benchmark configuration must contain a YAML mapping.")

    return EdgeRuntimeBenchmarkConfig.model_validate(raw_data)


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Return a linearly interpolated percentile for non-empty values."""

    if not values:
        raise ValueError("Cannot calculate a percentile for an empty sequence.")

    if not 0.0 <= percentile <= 100.0:
        raise ValueError("percentile must be between 0 and 100.")

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * (percentile / 100.0)
    lower_index = math.floor(position)
    upper_index = math.ceil(position)

    if lower_index == upper_index:
        return ordered[lower_index]

    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    fraction = position - lower_index

    return lower_value + ((upper_value - lower_value) * fraction)


def build_edge_runtime_benchmark_report(
    *,
    config: EdgeRuntimeBenchmarkConfig,
    samples: Sequence[EdgeRuntimeBenchmarkSample],
    torch_version: str,
) -> EdgeRuntimeBenchmarkReport:
    """Build a validated report from measured benchmark samples."""

    samples_by_case: dict[str, list[EdgeRuntimeBenchmarkSample]] = {
        case.name: [] for case in config.cases
    }

    for sample in samples:
        if sample.case_name not in samples_by_case:
            raise ValueError(f"Benchmark sample references unknown case: {sample.case_name!r}.")

        samples_by_case[sample.case_name].append(sample)

    summaries: list[EdgeRuntimeBenchmarkCaseSummary] = []

    for case in config.cases:
        case_samples = samples_by_case[case.name]

        if len(case_samples) != config.measured_iterations:
            raise ValueError(
                f"Benchmark case {case.name!r} requires "
                f"{config.measured_iterations} samples, got {len(case_samples)}."
            )

        iterations = [sample.iteration for sample in case_samples]

        if sorted(iterations) != list(range(1, config.measured_iterations + 1)):
            raise ValueError(
                f"Benchmark case {case.name!r} must contain each measured iteration once."
            )

        latencies = [sample.latency_ms for sample in case_samples]
        total_input_tokens = sum(sample.input_tokens for sample in case_samples)
        total_output_tokens = sum(sample.output_tokens for sample in case_samples)
        total_latency_ms = sum(latencies)

        summaries.append(
            EdgeRuntimeBenchmarkCaseSummary(
                case_name=case.name,
                device=case.device,
                dtype=case.dtype,
                adapter_path=(None if case.adapter_path is None else str(case.adapter_path)),
                sample_count=len(case_samples),
                mean_latency_ms=sum(latencies) / len(latencies),
                p50_latency_ms=_percentile(latencies, 50.0),
                p95_latency_ms=_percentile(latencies, 95.0),
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                output_tokens_per_second=(
                    None
                    if total_latency_ms <= 0.0 or total_output_tokens <= 0
                    else total_output_tokens / (total_latency_ms / 1000.0)
                ),
            )
        )

    return EdgeRuntimeBenchmarkReport(
        version=config.version,
        model_name=config.model_name,
        platform=platform.platform(),
        python_version=platform.python_version(),
        torch_version=torch_version,
        warmup_iterations=config.warmup_iterations,
        measured_iterations=config.measured_iterations,
        case_summaries=summaries,
        samples=list(samples),
    )


def render_edge_runtime_benchmark_markdown(
    report: EdgeRuntimeBenchmarkReport,
) -> str:
    """Render one compact Markdown benchmark report."""

    lines = [
        f"# Edge runtime benchmark v{report.version}",
        "",
        "## Environment",
        "",
        f"- Model: `{report.model_name}`",
        f"- Platform: `{report.platform}`",
        f"- Python: `{report.python_version}`",
        f"- PyTorch: `{report.torch_version}`",
        f"- Warm-up iterations per case: {report.warmup_iterations}",
        f"- Measured iterations per case: {report.measured_iterations}",
        "",
        "## Results",
        "",
        "| Case | Device | Dtype | Adapter | Mean latency | "
        "P50 latency | P95 latency | Output tok/s |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]

    for summary in report.case_summaries:
        adapter = "LoRA" if summary.adapter_path is not None else "Base"
        throughput = (
            "n/a"
            if summary.output_tokens_per_second is None
            else f"{summary.output_tokens_per_second:.2f}"
        )

        lines.append(
            "| "
            f"{summary.case_name} | "
            f"{summary.device} | "
            f"{summary.dtype} | "
            f"{adapter} | "
            f"{summary.mean_latency_ms:.2f} ms | "
            f"{summary.p50_latency_ms:.2f} ms | "
            f"{summary.p95_latency_ms:.2f} ms | "
            f"{throughput} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "These measurements compare local runtime configurations on one host.",
            "They do not claim Qualcomm QNN, Hexagon, or device-specific deployment performance.",
            "",
        ]
    )

    return "\n".join(lines)


def write_edge_runtime_benchmark_report(
    *,
    json_path: Path,
    markdown_path: Path,
    report: EdgeRuntimeBenchmarkReport,
) -> None:
    """Write JSON and Markdown benchmark artifacts."""

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_edge_runtime_benchmark_markdown(report),
        encoding="utf-8",
    )
