"""Tests for local edge-runtime benchmark execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aeroragx.generation.edge_runtime_benchmark import (
    EdgeRuntimeBenchmarkCase,
    EdgeRuntimeBenchmarkConfig,
)
from aeroragx.generation.edge_runtime_runner import (
    build_case_runtime_config,
    run_benchmark_case,
    run_edge_runtime_benchmark,
)
from aeroragx.generation.structured_provider import (
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)
from aeroragx.generation.transformers_transport import (
    TransformersRuntimeConfig,
)


class FakeTransport:
    """Deterministic transport that does not load a real model."""

    def __init__(self) -> None:
        self.requests: list[StructuredModelRequest] = []
        self.timeouts: list[float] = []

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        self.requests.append(request)
        self.timeouts.append(timeout_seconds)

        return StructuredModelResult(
            payload={
                "answer": "Grounded generation uses validated evidence.",
            },
            usage=ProviderUsage(
                input_tokens=11,
                output_tokens=5,
            ),
        )


class RecordingFactory:
    """Factory double that records every runtime configuration."""

    def __init__(self) -> None:
        self.configs: list[TransformersRuntimeConfig] = []
        self.transports: list[FakeTransport] = []

    def __call__(
        self,
        *,
        model_name: str,
        config: TransformersRuntimeConfig,
    ) -> FakeTransport:
        assert model_name == "Qwen/Qwen3-0.6B"

        transport = FakeTransport()

        self.configs.append(config)
        self.transports.append(transport)

        return transport


class SequenceClock:
    """Return deterministic timing boundaries."""

    def __init__(
        self,
        values: list[float],
    ) -> None:
        self._values = iter(values)

    def __call__(self) -> float:
        return next(self._values)


def make_benchmark_config() -> EdgeRuntimeBenchmarkConfig:
    """Build one small benchmark configuration for unit tests."""

    return EdgeRuntimeBenchmarkConfig(
        version="0.1",
        model_name="Qwen/Qwen3-0.6B",
        template_runtime_config=Path("configs/transformers_runtime_base_v0_2.yaml"),
        warmup_iterations=1,
        measured_iterations=3,
        timeout_seconds=12.5,
        max_input_tokens=256,
        max_new_tokens=32,
        system_prompt="Return valid JSON only.",
        user_prompt="Explain evidence-grounded generation.",
        cases=[
            EdgeRuntimeBenchmarkCase(
                name="lora_mps_float16",
                device="mps",
                dtype="float16",
                adapter_path=Path("artifacts/training/adapters/aeroragx_lora_v0_1_best"),
            ),
        ],
    )


def test_build_case_runtime_config_applies_benchmark_overrides() -> None:
    benchmark_config = make_benchmark_config()
    template_config = TransformersRuntimeConfig(
        device="auto",
        dtype="auto",
        max_input_tokens=16_000,
        max_new_tokens=768,
    )

    runtime_config = build_case_runtime_config(
        template_config=template_config,
        benchmark_config=benchmark_config,
        case=benchmark_config.cases[0],
    )

    assert runtime_config.device == "mps"
    assert runtime_config.dtype == "float16"
    assert runtime_config.max_input_tokens == 256
    assert runtime_config.max_new_tokens == 32
    assert runtime_config.adapter_path == Path(
        "artifacts/training/adapters/aeroragx_lora_v0_1_best"
    )


def test_run_benchmark_case_warms_up_measures_and_synchronizes() -> None:
    benchmark_config = make_benchmark_config()
    template_config = TransformersRuntimeConfig()
    factory = RecordingFactory()
    synchronized_devices: list[str] = []

    samples = run_benchmark_case(
        benchmark_config=benchmark_config,
        template_config=template_config,
        case=benchmark_config.cases[0],
        transport_factory=factory,
        clock=SequenceClock(
            [
                1.0,
                1.25,
                2.0,
                2.5,
                3.0,
                3.75,
            ]
        ),
        synchronize=synchronized_devices.append,
    )

    assert [sample.iteration for sample in samples] == [1, 2, 3]
    assert [sample.latency_ms for sample in samples] == pytest.approx([250.0, 500.0, 750.0])
    assert all(sample.input_tokens == 11 for sample in samples)
    assert all(sample.output_tokens == 5 for sample in samples)

    assert len(factory.configs) == 1
    assert len(factory.transports) == 1
    assert len(factory.transports[0].requests) == 4
    assert factory.transports[0].timeouts == [12.5, 12.5, 12.5, 12.5]
    assert synchronized_devices == ["mps"] * 8

    request = factory.transports[0].requests[0]
    assert request.model_name == "Qwen/Qwen3-0.6B"
    assert request.response_schema["required"] == ["answer"]


def test_run_edge_runtime_benchmark_writes_reports(
    tmp_path: Path,
) -> None:
    template_path = tmp_path / "runtime.yaml"
    template_path.write_text(
        (
            'version: "0.2"\n'
            'device: "auto"\n'
            'dtype: "auto"\n'
            "context_window_tokens: 32768\n"
            "max_input_tokens: 16000\n"
            "max_new_tokens: 768\n"
            "do_sample: false\n"
            "temperature: 0.7\n"
            "top_p: 0.8\n"
            "top_k: 20\n"
            "enable_thinking: false\n"
            "trust_remote_code: false\n"
            "local_files_only: true\n"
            "revision: null\n"
        ),
        encoding="utf-8",
    )

    benchmark_path = tmp_path / "benchmark.yaml"
    benchmark_path.write_text(
        (
            'version: "0.1"\n'
            'model_name: "Qwen/Qwen3-0.6B"\n'
            f'template_runtime_config: "{template_path}"\n'
            "warmup_iterations: 1\n"
            "measured_iterations: 2\n"
            "timeout_seconds: 12.5\n"
            "max_input_tokens: 256\n"
            "max_new_tokens: 32\n"
            'system_prompt: "Return valid JSON only."\n'
            'user_prompt: "Explain evidence-grounded generation."\n'
            "cases:\n"
            '  - name: "base_cpu_float32"\n'
            '    device: "cpu"\n'
            '    dtype: "float32"\n'
            "    adapter_path: null\n"
        ),
        encoding="utf-8",
    )

    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    factory = RecordingFactory()

    report = run_edge_runtime_benchmark(
        config_path=str(benchmark_path),
        json_report_path=str(json_path),
        markdown_report_path=str(markdown_path),
        transport_factory=factory,
    )

    written = json.loads(json_path.read_text(encoding="utf-8"))

    assert report.case_summaries[0].case_name == "base_cpu_float32"
    assert len(report.samples) == 2
    assert written["model_name"] == "Qwen/Qwen3-0.6B"
    assert "# Edge runtime benchmark v0.1" in markdown_path.read_text(encoding="utf-8")
    assert len(factory.transports[0].requests) == 3
