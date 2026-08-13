"""Tests for controlled MLX 4-bit versus Transformers MPS float16 reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aeroragx.generation.mlx_mps_runtime_comparison import (
    MlxMpsRuntimeComparisonConfig,
    RuntimeArtifact,
    RuntimeComparisonSample,
    build_mlx_comparison_config,
    build_mlx_mps_runtime_comparison_report,
    build_transformers_comparison_config,
    load_mlx_mps_runtime_comparison_config,
    render_mlx_mps_runtime_comparison_markdown,
    write_mlx_mps_runtime_comparison_report,
)
from aeroragx.generation.mlx_transport import MLXRuntimeConfig
from aeroragx.generation.transformers_transport import TransformersRuntimeConfig


def make_config(**overrides: object) -> MlxMpsRuntimeComparisonConfig:
    """Build one valid compact controlled-comparison definition."""

    values: dict[str, object] = {
        "version": "0.1",
        "source_model_name": "Qwen/Qwen3-0.6B",
        "transformers_model_name": "Qwen/Qwen3-0.6B",
        "transformers_runtime_config": Path("configs/transformers_runtime_base_v0_2.yaml"),
        "mlx_model_path": Path("artifacts/models/qwen3_0_6b_mlx_4bit"),
        "mlx_runtime_config": Path("configs/mlx_runtime_v0_1.yaml"),
        "warmup_iterations": 1,
        "measured_iterations": 3,
        "timeout_seconds": 120.0,
        "max_input_tokens": 2048,
        "max_new_tokens": 96,
        "system_prompt": "Return valid JSON only.",
        "user_prompt": "Explain grounded generation.",
    }
    values.update(overrides)
    return MlxMpsRuntimeComparisonConfig.model_validate(values)


def make_artifacts() -> list[RuntimeArtifact]:
    """Build deterministic artifact metadata for both required conditions."""

    return [
        RuntimeArtifact(
            runtime="transformers_mps_float16",
            model_identifier="Qwen/Qwen3-0.6B",
            local_path="/tmp/qwen-base",
            artifact_size_mib=1000.0,
        ),
        RuntimeArtifact(
            runtime="mlx_4bit_affine_g128",
            model_identifier="artifacts/models/qwen3_0_6b_mlx_4bit",
            local_path="artifacts/models/qwen3_0_6b_mlx_4bit",
            artifact_size_mib=313.1,
            quantization={"bits": 4, "group_size": 128, "mode": "affine"},
        ),
    ]


def make_samples() -> list[RuntimeComparisonSample]:
    """Build three valid deterministic samples for each condition."""

    samples: list[RuntimeComparisonSample] = []

    for runtime, latencies in (
        ("transformers_mps_float16", [100.0, 200.0, 300.0]),
        ("mlx_4bit_affine_g128", [50.0, 100.0, 150.0]),
    ):
        for iteration, latency_ms in enumerate(latencies, start=1):
            samples.append(
                RuntimeComparisonSample(
                    runtime=runtime,
                    iteration=iteration,
                    latency_ms=latency_ms,
                    input_tokens=10,
                    output_tokens=20,
                    json_valid=True,
                )
            )

    return samples


def test_load_config(tmp_path: Path) -> None:
    path = tmp_path / "comparison.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            'source_model_name: "Qwen/Qwen3-0.6B"\n'
            'transformers_model_name: "Qwen/Qwen3-0.6B"\n'
            'transformers_runtime_config: "configs/transformers_runtime_base_v0_2.yaml"\n'
            'mlx_model_path: "artifacts/models/qwen3_0_6b_mlx_4bit"\n'
            'mlx_runtime_config: "configs/mlx_runtime_v0_1.yaml"\n'
            "warmup_iterations: 1\n"
            "measured_iterations: 3\n"
            "timeout_seconds: 120.0\n"
            "max_input_tokens: 2048\n"
            "max_new_tokens: 96\n"
            'system_prompt: "Return JSON."\n'
            'user_prompt: "Explain grounded generation."\n'
        ),
        encoding="utf-8",
    )

    config = load_mlx_mps_runtime_comparison_config(path)

    assert config.mlx_model_path.name == "qwen3_0_6b_mlx_4bit"
    assert config.max_new_tokens == 96


def test_config_rejects_context_budget_overflow() -> None:
    with pytest.raises(ValidationError, match="must not exceed 32768"):
        make_config(max_input_tokens=32_000, max_new_tokens=769)


def test_runtime_configs_share_budget_and_enforce_determinism() -> None:
    config = make_config()
    transformers_config = build_transformers_comparison_config(
        template_config=TransformersRuntimeConfig(
            device="auto",
            dtype="auto",
            do_sample=False,
            enable_thinking=False,
        ),
        benchmark_config=config,
    )
    mlx_config = build_mlx_comparison_config(
        template_config=MLXRuntimeConfig(
            context_window_tokens=32_768,
            max_input_tokens=16_000,
            max_new_tokens=512,
            temperature=0.0,
            top_p=0.0,
            min_p=0.0,
            top_k=0,
            enable_thinking=False,
        ),
        benchmark_config=config,
    )

    assert transformers_config.device == "mps"
    assert transformers_config.dtype == "float16"
    assert transformers_config.max_input_tokens == mlx_config.max_input_tokens == 2048
    assert transformers_config.max_new_tokens == mlx_config.max_new_tokens == 96


def test_report_aggregates_both_runtime_conditions() -> None:
    report = build_mlx_mps_runtime_comparison_report(
        config=make_config(),
        artifacts=make_artifacts(),
        samples=make_samples(),
        package_versions={"mlx-lm": "test", "PyTorch": "test"},
    )

    transformers_summary = report.summaries[0]
    mlx_summary = report.summaries[1]

    assert transformers_summary.mean_latency_ms == pytest.approx(200.0)
    assert transformers_summary.p95_latency_ms == pytest.approx(290.0)
    assert transformers_summary.output_tokens_per_second == pytest.approx(100.0)
    assert mlx_summary.mean_latency_ms == pytest.approx(100.0)
    assert mlx_summary.valid_json_count == 3
    assert mlx_summary.output_tokens_per_second == pytest.approx(200.0)


def test_write_report_outputs_json_and_markdown(tmp_path: Path) -> None:
    report = build_mlx_mps_runtime_comparison_report(
        config=make_config(),
        artifacts=make_artifacts(),
        samples=make_samples(),
        package_versions={"mlx-lm": "test", "PyTorch": "test"},
    )
    json_path = tmp_path / "comparison.json"
    markdown_path = tmp_path / "comparison.md"

    write_mlx_mps_runtime_comparison_report(
        json_path=json_path,
        markdown_path=markdown_path,
        report=report,
    )

    written = json.loads(json_path.read_text(encoding="utf-8"))

    assert written["version"] == "0.1"
    assert written["artifacts"][1]["quantization"]["bits"] == 4
    markdown = render_mlx_mps_runtime_comparison_markdown(report)
    assert "# MLX 4-bit versus Transformers MPS float16 comparison v0.1" in markdown
    assert "Total input tokens" in markdown
    assert "Total output tokens" in markdown
