"""Tests for edge-runtime benchmark configuration and reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from aeroragx.generation.edge_runtime_benchmark import (
    EdgeRuntimeBenchmarkCase,
    EdgeRuntimeBenchmarkConfig,
    EdgeRuntimeBenchmarkSample,
    build_edge_runtime_benchmark_report,
    load_edge_runtime_benchmark_config,
    render_edge_runtime_benchmark_markdown,
    write_edge_runtime_benchmark_report,
)


def make_config(
    **overrides: object,
) -> EdgeRuntimeBenchmarkConfig:
    """Build one valid compact benchmark configuration."""

    values: dict[str, object] = {
        "version": "0.1",
        "model_name": "Qwen/Qwen3-0.6B",
        "template_runtime_config": Path("configs/transformers_runtime_base_v0_2.yaml"),
        "warmup_iterations": 1,
        "measured_iterations": 3,
        "timeout_seconds": 120.0,
        "max_input_tokens": 2048,
        "max_new_tokens": 96,
        "system_prompt": "Return valid JSON only.",
        "user_prompt": "Explain grounded generation.",
        "cases": [
            EdgeRuntimeBenchmarkCase(
                name="base_cpu_float32",
                device="cpu",
                dtype="float32",
            ),
            EdgeRuntimeBenchmarkCase(
                name="base_mps_float16",
                device="mps",
                dtype="float16",
            ),
        ],
    }

    values.update(overrides)

    return EdgeRuntimeBenchmarkConfig.model_validate(values)


def make_samples() -> list[EdgeRuntimeBenchmarkSample]:
    """Create deterministic samples for two benchmark cases."""

    return [
        EdgeRuntimeBenchmarkSample(
            case_name="base_cpu_float32",
            iteration=1,
            latency_ms=100.0,
            input_tokens=10,
            output_tokens=20,
        ),
        EdgeRuntimeBenchmarkSample(
            case_name="base_cpu_float32",
            iteration=2,
            latency_ms=200.0,
            input_tokens=10,
            output_tokens=20,
        ),
        EdgeRuntimeBenchmarkSample(
            case_name="base_cpu_float32",
            iteration=3,
            latency_ms=300.0,
            input_tokens=10,
            output_tokens=20,
        ),
        EdgeRuntimeBenchmarkSample(
            case_name="base_mps_float16",
            iteration=1,
            latency_ms=50.0,
            input_tokens=10,
            output_tokens=20,
        ),
        EdgeRuntimeBenchmarkSample(
            case_name="base_mps_float16",
            iteration=2,
            latency_ms=100.0,
            input_tokens=10,
            output_tokens=20,
        ),
        EdgeRuntimeBenchmarkSample(
            case_name="base_mps_float16",
            iteration=3,
            latency_ms=150.0,
            input_tokens=10,
            output_tokens=20,
        ),
    ]


def test_load_edge_runtime_benchmark_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "benchmark.yaml"
    path.write_text(
        (
            'version: "0.1"\n'
            'model_name: "Qwen/Qwen3-0.6B"\n'
            'template_runtime_config: "configs/transformers_runtime_base_v0_2.yaml"\n'
            "warmup_iterations: 1\n"
            "measured_iterations: 3\n"
            "timeout_seconds: 120.0\n"
            "max_input_tokens: 2048\n"
            "max_new_tokens: 96\n"
            'system_prompt: "Return JSON."\n'
            'user_prompt: "Explain grounded generation."\n'
            "cases:\n"
            '  - name: "base_cpu_float32"\n'
            '    device: "cpu"\n'
            '    dtype: "float32"\n'
            "    adapter_path: null\n"
        ),
        encoding="utf-8",
    )

    config = load_edge_runtime_benchmark_config(path)

    assert config.model_name == "Qwen/Qwen3-0.6B"
    assert config.cases[0].name == "base_cpu_float32"


def test_config_rejects_duplicate_case_names() -> None:
    duplicate_case = EdgeRuntimeBenchmarkCase(
        name="base_cpu_float32",
        device="cpu",
        dtype="float32",
    )

    with pytest.raises(
        ValidationError,
        match="Benchmark case names must be unique",
    ):
        make_config(
            cases=[
                duplicate_case,
                duplicate_case,
            ]
        )


def test_build_report_aggregates_case_statistics() -> None:
    report = build_edge_runtime_benchmark_report(
        config=make_config(),
        samples=make_samples(),
        torch_version="test-torch",
    )

    cpu_summary = report.case_summaries[0]
    mps_summary = report.case_summaries[1]

    assert cpu_summary.mean_latency_ms == pytest.approx(200.0)
    assert cpu_summary.p50_latency_ms == pytest.approx(200.0)
    assert cpu_summary.p95_latency_ms == pytest.approx(290.0)
    assert cpu_summary.output_tokens_per_second == pytest.approx(100.0)

    assert mps_summary.mean_latency_ms == pytest.approx(100.0)
    assert mps_summary.output_tokens_per_second == pytest.approx(200.0)


def test_report_rejects_missing_case_samples() -> None:
    with pytest.raises(
        ValueError,
        match="requires 3 samples",
    ):
        build_edge_runtime_benchmark_report(
            config=make_config(),
            samples=make_samples()[:3],
            torch_version="test-torch",
        )


def test_write_report_outputs_json_and_markdown(
    tmp_path: Path,
) -> None:
    report = build_edge_runtime_benchmark_report(
        config=make_config(),
        samples=make_samples(),
        torch_version="test-torch",
    )

    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"

    write_edge_runtime_benchmark_report(
        json_path=json_path,
        markdown_path=markdown_path,
        report=report,
    )

    written = json.loads(json_path.read_text(encoding="utf-8"))

    assert written["model_name"] == "Qwen/Qwen3-0.6B"
    assert "# Edge runtime benchmark v0.1" in markdown_path.read_text(encoding="utf-8")
    assert "base_mps_float16" in render_edge_runtime_benchmark_markdown(report)
