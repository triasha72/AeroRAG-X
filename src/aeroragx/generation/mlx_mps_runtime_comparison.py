"""Controlled Apple-Silicon MLX versus Transformers MPS runtime comparison."""

from __future__ import annotations

import json
import math
import platform
from collections.abc import Callable, Sequence
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from pathlib import Path
from time import perf_counter
from typing import Literal

import torch
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.generation.mlx_transport import (
    MLXRuntimeConfig,
    MLXStructuredModelTransport,
    load_mlx_runtime_config,
)
from aeroragx.generation.structured_provider import (
    StructuredModelRequest,
    StructuredModelResult,
    StructuredModelTransport,
)
from aeroragx.generation.transformers_transport import (
    TransformersRuntimeConfig,
    TransformersStructuredModelTransport,
    load_transformers_runtime_config,
)

type RuntimeName = Literal["transformers_mps_float16", "mlx_4bit_affine_g128"]

_RESPONSE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


class MlxMpsRuntimeComparisonConfig(BaseModel):
    """Immutable workload definition for one cross-runtime comparison."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: str = "0.1"
    source_model_name: str = Field(min_length=1)
    transformers_model_name: str = Field(min_length=1)
    transformers_runtime_config: Path
    mlx_model_path: Path
    mlx_runtime_config: Path
    warmup_iterations: int = Field(ge=0, le=10)
    measured_iterations: int = Field(ge=1, le=20)
    timeout_seconds: float = Field(gt=0.0, le=600.0)
    max_input_tokens: int = Field(ge=1)
    max_new_tokens: int = Field(ge=1)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_budget(self) -> MlxMpsRuntimeComparisonConfig:
        """Keep both runtime conditions inside the shared Qwen context budget."""

        if self.max_input_tokens + self.max_new_tokens > 32_768:
            raise ValueError("max_input_tokens + max_new_tokens must not exceed 32768.")

        return self


class RuntimeArtifact(BaseModel):
    """Reproducibility metadata for one locally available model artifact."""

    model_config = ConfigDict(extra="forbid")

    runtime: RuntimeName
    model_identifier: str = Field(min_length=1)
    local_path: str | None = None
    artifact_size_mib: float = Field(ge=0.0)
    quantization: dict[str, object] | None = None


class RuntimeComparisonSample(BaseModel):
    """One measured structured completion after warm-up."""

    model_config = ConfigDict(extra="forbid")

    runtime: RuntimeName
    iteration: int = Field(ge=1)
    latency_ms: float = Field(ge=0.0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    json_valid: bool


class RuntimeComparisonSummary(BaseModel):
    """Aggregated metrics for one runtime condition."""

    model_config = ConfigDict(extra="forbid")

    runtime: RuntimeName
    sample_count: int = Field(ge=1)
    valid_json_count: int = Field(ge=0)
    mean_latency_ms: float = Field(ge=0.0)
    p50_latency_ms: float = Field(ge=0.0)
    p95_latency_ms: float = Field(ge=0.0)
    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)
    output_tokens_per_second: float | None = Field(default=None, ge=0.0)


class MlxMpsRuntimeComparisonReport(BaseModel):
    """Versioned report for the controlled local cross-runtime comparison."""

    model_config = ConfigDict(extra="forbid")

    version: str
    source_model_name: str
    platform: str
    python_version: str
    package_versions: dict[str, str]
    warmup_iterations: int = Field(ge=0)
    measured_iterations: int = Field(ge=1)
    max_input_tokens: int = Field(ge=1)
    max_new_tokens: int = Field(ge=1)
    artifacts: list[RuntimeArtifact] = Field(min_length=2)
    summaries: list[RuntimeComparisonSummary] = Field(min_length=2)
    samples: list[RuntimeComparisonSample] = Field(min_length=2)


def load_mlx_mps_runtime_comparison_config(
    path: Path,
) -> MlxMpsRuntimeComparisonConfig:
    """Load and validate a controlled cross-runtime benchmark YAML mapping."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("MLX/MPS comparison configuration must contain a YAML mapping.")

    return MlxMpsRuntimeComparisonConfig.model_validate(raw_data)


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Return a linearly interpolated percentile for a non-empty sequence."""

    if not values:
        raise ValueError("Cannot calculate a percentile for an empty sequence.")

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
    return lower_value + ((upper_value - lower_value) * (position - lower_index))


def _usage_tokens(result: StructuredModelResult) -> tuple[int, int]:
    """Return non-negative usage values when a transport omits metadata."""

    if result.usage is None:
        return 0, 0

    return result.usage.input_tokens or 0, result.usage.output_tokens or 0


def _validate_structured_result(result: StructuredModelResult) -> bool:
    """Validate the fixed benchmark response contract after transport parsing."""

    answer = result.payload.get("answer")
    return isinstance(answer, str) and bool(answer.strip())


def build_comparison_request(
    *,
    model_name: str,
    config: MlxMpsRuntimeComparisonConfig,
) -> StructuredModelRequest:
    """Build the identical structured workload for either runtime."""

    return StructuredModelRequest(
        model_name=model_name,
        system_prompt=config.system_prompt,
        user_prompt=config.user_prompt,
        response_schema=_RESPONSE_SCHEMA,
    )


def build_transformers_comparison_config(
    *,
    template_config: TransformersRuntimeConfig,
    benchmark_config: MlxMpsRuntimeComparisonConfig,
) -> TransformersRuntimeConfig:
    """Apply the fixed MPS float16 and shared budget requirements."""

    if template_config.do_sample:
        raise ValueError("The controlled Transformers condition requires do_sample: false.")

    if template_config.enable_thinking:
        raise ValueError("The controlled Transformers condition requires enable_thinking: false.")

    return template_config.model_copy(
        update={
            "device": "mps",
            "dtype": "float16",
            "max_input_tokens": benchmark_config.max_input_tokens,
            "max_new_tokens": benchmark_config.max_new_tokens,
        }
    )


def build_mlx_comparison_config(
    *,
    template_config: MLXRuntimeConfig,
    benchmark_config: MlxMpsRuntimeComparisonConfig,
) -> MLXRuntimeConfig:
    """Apply the shared budget and deterministic MLX sampling requirements."""

    if template_config.enable_thinking:
        raise ValueError("The controlled MLX condition requires enable_thinking: false.")

    if any(
        value != 0
        for value in (
            template_config.temperature,
            template_config.top_p,
            template_config.min_p,
            template_config.top_k,
        )
    ):
        raise ValueError("The controlled MLX condition requires deterministic zero sampling.")

    return template_config.model_copy(
        update={
            "max_input_tokens": benchmark_config.max_input_tokens,
            "max_new_tokens": benchmark_config.max_new_tokens,
        }
    )


def _run_runtime(
    *,
    runtime: RuntimeName,
    model_name: str,
    transport: StructuredModelTransport,
    benchmark_config: MlxMpsRuntimeComparisonConfig,
    synchronize: Callable[[], None],
    clock: Callable[[], float] = perf_counter,
) -> list[RuntimeComparisonSample]:
    """Warm up and measure one already loaded transport under fixed conditions."""

    request = build_comparison_request(model_name=model_name, config=benchmark_config)

    for _ in range(benchmark_config.warmup_iterations):
        synchronize()
        warmup_result = transport.complete(
            request=request,
            timeout_seconds=benchmark_config.timeout_seconds,
        )
        synchronize()

        if not _validate_structured_result(warmup_result):
            raise ValueError(f"{runtime} warm-up did not return a valid answer payload.")

    samples: list[RuntimeComparisonSample] = []

    for iteration in range(1, benchmark_config.measured_iterations + 1):
        synchronize()
        started_at = clock()
        result = transport.complete(
            request=request,
            timeout_seconds=benchmark_config.timeout_seconds,
        )
        synchronize()
        latency_ms = (clock() - started_at) * 1000.0
        input_tokens, output_tokens = _usage_tokens(result)

        samples.append(
            RuntimeComparisonSample(
                runtime=runtime,
                iteration=iteration,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                json_valid=_validate_structured_result(result),
            )
        )

    return samples


def _directory_size_mib(path: Path) -> float:
    """Return the cumulative size of regular files beneath one local artifact."""

    if not path.is_dir():
        raise ValueError(f"Required local artifact directory does not exist: {path}")

    total_bytes = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    return total_bytes / (1024**2)


def inspect_mlx_artifact(path: Path) -> RuntimeArtifact:
    """Read the local MLX artifact size and required affine 4-bit metadata."""

    config_path = path / "config.json"

    if not config_path.is_file():
        raise ValueError(f"MLX artifact is missing config.json: {path}")

    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    quantization = raw_config.get("quantization") or raw_config.get("quantization_config")

    if not isinstance(quantization, dict):
        raise ValueError("MLX artifact is missing quantization metadata.")

    if int(quantization.get("bits", -1)) != 4:
        raise ValueError("Controlled MLX artifact must use 4-bit weights.")

    if int(quantization.get("group_size", -1)) != 128:
        raise ValueError("Controlled MLX artifact must use group size 128.")

    if str(quantization.get("mode", "")) != "affine":
        raise ValueError("Controlled MLX artifact must use affine quantization.")

    if not list(path.rglob("*.safetensors")):
        raise ValueError("MLX artifact has no safetensors weights.")

    return RuntimeArtifact(
        runtime="mlx_4bit_affine_g128",
        model_identifier=str(path),
        local_path=str(path),
        artifact_size_mib=_directory_size_mib(path),
        quantization={str(key): value for key, value in quantization.items()},
    )


def inspect_transformers_artifact(model_name: str) -> RuntimeArtifact:
    """Resolve the locally cached Transformers base artifact without downloading it."""

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise ValueError("Transformers artifact inspection requires huggingface-hub.") from exc

    try:
        snapshot = Path(snapshot_download(repo_id=model_name, local_files_only=True))
    except Exception as exc:
        raise ValueError(
            f"Transformers model {model_name!r} is not available in the local cache."
        ) from exc

    return RuntimeArtifact(
        runtime="transformers_mps_float16",
        model_identifier=model_name,
        local_path=str(snapshot),
        artifact_size_mib=_directory_size_mib(snapshot),
        quantization=None,
    )


def _installed_version(distribution_name: str) -> str:
    """Return a package version without making a missing optional package fatal."""

    try:
        return distribution_version(distribution_name)
    except PackageNotFoundError:
        return "not-installed"


def build_mlx_mps_runtime_comparison_report(
    *,
    config: MlxMpsRuntimeComparisonConfig,
    artifacts: Sequence[RuntimeArtifact],
    samples: Sequence[RuntimeComparisonSample],
    package_versions: dict[str, str],
) -> MlxMpsRuntimeComparisonReport:
    """Aggregate validated samples into a reproducible comparison report."""

    expected_runtimes: tuple[RuntimeName, RuntimeName] = (
        "transformers_mps_float16",
        "mlx_4bit_affine_g128",
    )

    artifacts_by_runtime = {artifact.runtime: artifact for artifact in artifacts}

    if set(artifacts_by_runtime) != set(expected_runtimes):
        raise ValueError("Comparison report requires one artifact for each runtime.")

    samples_by_runtime: dict[RuntimeName, list[RuntimeComparisonSample]] = {
        runtime: [] for runtime in expected_runtimes
    }

    for sample in samples:
        samples_by_runtime[sample.runtime].append(sample)

    summaries: list[RuntimeComparisonSummary] = []

    for runtime in expected_runtimes:
        runtime_samples = samples_by_runtime[runtime]

        if len(runtime_samples) != config.measured_iterations:
            raise ValueError(
                f"Runtime {runtime!r} requires {config.measured_iterations} samples, "
                f"got {len(runtime_samples)}."
            )

        if sorted(sample.iteration for sample in runtime_samples) != list(
            range(1, config.measured_iterations + 1)
        ):
            raise ValueError(f"Runtime {runtime!r} must contain each measured iteration once.")

        latencies = [sample.latency_ms for sample in runtime_samples]
        total_latency_ms = sum(latencies)
        total_output_tokens = sum(sample.output_tokens for sample in runtime_samples)

        summaries.append(
            RuntimeComparisonSummary(
                runtime=runtime,
                sample_count=len(runtime_samples),
                valid_json_count=sum(sample.json_valid for sample in runtime_samples),
                mean_latency_ms=total_latency_ms / len(runtime_samples),
                p50_latency_ms=_percentile(latencies, 50.0),
                p95_latency_ms=_percentile(latencies, 95.0),
                total_input_tokens=sum(sample.input_tokens for sample in runtime_samples),
                total_output_tokens=total_output_tokens,
                output_tokens_per_second=(
                    None
                    if total_latency_ms <= 0.0 or total_output_tokens <= 0
                    else total_output_tokens / (total_latency_ms / 1000.0)
                ),
            )
        )

    return MlxMpsRuntimeComparisonReport(
        version=config.version,
        source_model_name=config.source_model_name,
        platform=platform.platform(),
        python_version=platform.python_version(),
        package_versions=package_versions,
        warmup_iterations=config.warmup_iterations,
        measured_iterations=config.measured_iterations,
        max_input_tokens=config.max_input_tokens,
        max_new_tokens=config.max_new_tokens,
        artifacts=[artifacts_by_runtime[runtime] for runtime in expected_runtimes],
        summaries=summaries,
        samples=list(samples),
    )


def render_mlx_mps_runtime_comparison_markdown(
    report: MlxMpsRuntimeComparisonReport,
) -> str:
    """Render a compact Markdown report with reproducibility limitations."""

    lines = [
        f"# MLX 4-bit versus Transformers MPS float16 comparison v{report.version}",
        "",
        "## Environment",
        "",
        f"- Source model: `{report.source_model_name}`",
        f"- Platform: `{report.platform}`",
        f"- Python: `{report.python_version}`",
    ]

    for name, package_version in sorted(report.package_versions.items()):
        lines.append(f"- {name}: `{package_version}`")

    lines.extend(
        [
            "",
            "## Controlled workload",
            "",
            f"- Warm-up iterations per runtime: {report.warmup_iterations}",
            f"- Measured iterations per runtime: {report.measured_iterations}",
            f"- Maximum input tokens: {report.max_input_tokens}",
            f"- Maximum new tokens: {report.max_new_tokens}",
            "- Both conditions use the same structured prompt and JSON schema.",
            "- Transformers uses MPS float16 with greedy decoding.",
            (
                "- MLX uses the local affine 4-bit, group-size-128 artifact "
                "with deterministic sampling."
            ),
            "",
            "## Artifacts",
            "",
            "| Runtime | Model identifier | Artifact size | Quantization |",
            "|---|---|---:|---|",
        ]
    )

    for artifact in report.artifacts:
        quantization = (
            "n/a"
            if artifact.quantization is None
            else json.dumps(artifact.quantization, sort_keys=True)
        )
        lines.append(
            "| "
            f"{artifact.runtime} | `{artifact.model_identifier}` | "
            f"{artifact.artifact_size_mib:.2f} MiB | `{quantization}` |"
        )

    lines.extend(
        [
            "",
            "## Results",
            "",
            (
                "| Runtime | Valid JSON | Mean latency | P50 latency | P95 latency | "
                "Output tok/s | Total input tokens | Total output tokens |"
            ),
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for summary in report.summaries:
        throughput = (
            "n/a"
            if summary.output_tokens_per_second is None
            else f"{summary.output_tokens_per_second:.2f}"
        )
        lines.append(
            "| "
            f"{summary.runtime} | "
            f"{summary.valid_json_count}/{summary.sample_count} | "
            f"{summary.mean_latency_ms:.2f} ms | "
            f"{summary.p50_latency_ms:.2f} ms | "
            f"{summary.p95_latency_ms:.2f} ms | "
            f"{throughput} | "
            f"{summary.total_input_tokens} | "
            f"{summary.total_output_tokens} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation limits",
            "",
            "- Model construction and loading are excluded from per-request latency.",
            "- MPS and MLX work are synchronized at timing boundaries.",
            (
                "- These are one-host local measurements, not Qualcomm QNN, "
                "Hexagon, or device-deployment measurements."
            ),
            (
                "- Latency and throughput do not establish output-quality "
                "equivalence; totals are reported across measured iterations."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def write_mlx_mps_runtime_comparison_report(
    *,
    json_path: Path,
    markdown_path: Path,
    report: MlxMpsRuntimeComparisonReport,
) -> None:
    """Write JSON and Markdown artifacts for one completed comparison."""

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_mlx_mps_runtime_comparison_markdown(report),
        encoding="utf-8",
    )


def run_mlx_mps_runtime_comparison(
    *,
    config_path: str,
    json_report_path: str,
    markdown_report_path: str,
    clock: Callable[[], float] = perf_counter,
) -> MlxMpsRuntimeComparisonReport:
    """Run the controlled comparison and persist its versioned report artifacts."""

    config = load_mlx_mps_runtime_comparison_config(Path(config_path))
    transformers_template = load_transformers_runtime_config(config.transformers_runtime_config)
    mlx_template = load_mlx_runtime_config(config.mlx_runtime_config)

    transformers_config = build_transformers_comparison_config(
        template_config=transformers_template,
        benchmark_config=config,
    )
    mlx_config = build_mlx_comparison_config(
        template_config=mlx_template,
        benchmark_config=config,
    )

    if not torch.backends.mps.is_available():
        raise ValueError("The controlled Transformers condition requires an available MPS device.")

    try:
        import mlx.core as mx
        import mlx_lm
    except ImportError as exc:
        raise ValueError(
            "The controlled MLX condition requires the macOS arm64 mlx extra."
        ) from exc

    if not callable(getattr(mx, "synchronize", None)):
        raise ValueError("The installed MLX runtime does not provide mx.synchronize().")

    transformers_transport = TransformersStructuredModelTransport(
        model_name=config.transformers_model_name,
        config=transformers_config,
    )
    mlx_transport = MLXStructuredModelTransport(
        model_name=str(config.mlx_model_path),
        config=mlx_config,
    )

    samples = _run_runtime(
        runtime="transformers_mps_float16",
        model_name=config.transformers_model_name,
        transport=transformers_transport,
        benchmark_config=config,
        synchronize=torch.mps.synchronize,
        clock=clock,
    )
    samples.extend(
        _run_runtime(
            runtime="mlx_4bit_affine_g128",
            model_name=str(config.mlx_model_path),
            transport=mlx_transport,
            benchmark_config=config,
            synchronize=mx.synchronize,
            clock=clock,
        )
    )

    package_versions = {
        "mlx": getattr(mx, "__version__", _installed_version("mlx")),
        "mlx-lm": getattr(mlx_lm, "__version__", _installed_version("mlx-lm")),
        "PyTorch": torch.__version__,
        "Transformers": _installed_version("transformers"),
    }
    artifacts = [
        inspect_transformers_artifact(config.transformers_model_name),
        inspect_mlx_artifact(config.mlx_model_path),
    ]
    report = build_mlx_mps_runtime_comparison_report(
        config=config,
        artifacts=artifacts,
        samples=samples,
        package_versions=package_versions,
    )
    write_mlx_mps_runtime_comparison_report(
        json_path=Path(json_report_path),
        markdown_path=Path(markdown_report_path),
        report=report,
    )

    return report
