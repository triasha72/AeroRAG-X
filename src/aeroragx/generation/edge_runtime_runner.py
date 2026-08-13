"""Execution utilities for reproducible local edge-runtime benchmarks."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Protocol

import torch

from aeroragx.generation.edge_runtime_benchmark import (
    EdgeRuntimeBenchmarkCase,
    EdgeRuntimeBenchmarkConfig,
    EdgeRuntimeBenchmarkReport,
    EdgeRuntimeBenchmarkSample,
    build_edge_runtime_benchmark_report,
    load_edge_runtime_benchmark_config,
    write_edge_runtime_benchmark_report,
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

_RESPONSE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
        },
    },
    "required": ["answer"],
    "additionalProperties": False,
}


class EdgeRuntimeTransportFactory(Protocol):
    """Construct one configured local structured-generation transport."""

    def __call__(
        self,
        *,
        model_name: str,
        config: TransformersRuntimeConfig,
    ) -> StructuredModelTransport:
        """Create one transport for a benchmark case."""


def create_transformers_transport(
    *,
    model_name: str,
    config: TransformersRuntimeConfig,
) -> TransformersStructuredModelTransport:
    """Create the production local Transformers transport."""

    return TransformersStructuredModelTransport(
        model_name=model_name,
        config=config,
    )


def synchronize_device(
    device_name: str,
) -> None:
    """Wait for asynchronous device work before taking a timing boundary."""

    if device_name == "mps" and torch.backends.mps.is_available():
        torch.mps.synchronize()

    elif device_name == "cuda" and torch.cuda.is_available():
        torch.cuda.synchronize()


def build_case_runtime_config(
    *,
    template_config: TransformersRuntimeConfig,
    benchmark_config: EdgeRuntimeBenchmarkConfig,
    case: EdgeRuntimeBenchmarkCase,
) -> TransformersRuntimeConfig:
    """Apply one benchmark case's device, dtype, adapter, and token limits."""

    return template_config.model_copy(
        update={
            "device": case.device,
            "dtype": case.dtype,
            "adapter_path": case.adapter_path,
            "max_input_tokens": benchmark_config.max_input_tokens,
            "max_new_tokens": benchmark_config.max_new_tokens,
        }
    )


def build_benchmark_request(
    config: EdgeRuntimeBenchmarkConfig,
) -> StructuredModelRequest:
    """Build the fixed structured request used for every benchmark sample."""

    return StructuredModelRequest(
        model_name=config.model_name,
        system_prompt=config.system_prompt,
        user_prompt=config.user_prompt,
        response_schema=_RESPONSE_SCHEMA,
    )


def _usage_tokens(
    result: StructuredModelResult,
) -> tuple[int, int]:
    """Return non-negative usage values when a transport omits token metadata."""

    if result.usage is None:
        return 0, 0

    return (
        result.usage.input_tokens or 0,
        result.usage.output_tokens or 0,
    )


def run_benchmark_case(
    *,
    benchmark_config: EdgeRuntimeBenchmarkConfig,
    template_config: TransformersRuntimeConfig,
    case: EdgeRuntimeBenchmarkCase,
    transport_factory: EdgeRuntimeTransportFactory = create_transformers_transport,
    clock: Callable[[], float] = perf_counter,
    synchronize: Callable[[str], None] = synchronize_device,
) -> list[EdgeRuntimeBenchmarkSample]:
    """Warm up and measure one local runtime configuration."""

    runtime_config = build_case_runtime_config(
        template_config=template_config,
        benchmark_config=benchmark_config,
        case=case,
    )
    transport = transport_factory(
        model_name=benchmark_config.model_name,
        config=runtime_config,
    )
    request = build_benchmark_request(benchmark_config)

    for _ in range(benchmark_config.warmup_iterations):
        synchronize(case.device)
        transport.complete(
            request=request,
            timeout_seconds=benchmark_config.timeout_seconds,
        )
        synchronize(case.device)

    samples: list[EdgeRuntimeBenchmarkSample] = []

    for iteration in range(1, benchmark_config.measured_iterations + 1):
        synchronize(case.device)
        started_at = clock()

        result = transport.complete(
            request=request,
            timeout_seconds=benchmark_config.timeout_seconds,
        )

        synchronize(case.device)
        elapsed_seconds = clock() - started_at
        input_tokens, output_tokens = _usage_tokens(result)

        samples.append(
            EdgeRuntimeBenchmarkSample(
                case_name=case.name,
                iteration=iteration,
                latency_ms=elapsed_seconds * 1000.0,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )

    return samples


def run_edge_runtime_benchmark(
    *,
    config_path: str,
    json_report_path: str,
    markdown_report_path: str,
    transport_factory: EdgeRuntimeTransportFactory = create_transformers_transport,
) -> EdgeRuntimeBenchmarkReport:
    """Execute all benchmark cases and write validated JSON and Markdown reports."""

    benchmark_config = load_edge_runtime_benchmark_config(
        Path(config_path),
    )
    template_config = load_transformers_runtime_config(
        benchmark_config.template_runtime_config,
    )

    samples: list[EdgeRuntimeBenchmarkSample] = []

    for case in benchmark_config.cases:
        samples.extend(
            run_benchmark_case(
                benchmark_config=benchmark_config,
                template_config=template_config,
                case=case,
                transport_factory=transport_factory,
            )
        )

    report = build_edge_runtime_benchmark_report(
        config=benchmark_config,
        samples=samples,
        torch_version=torch.__version__,
    )
    write_edge_runtime_benchmark_report(
        json_path=Path(json_report_path),
        markdown_path=Path(markdown_report_path),
        report=report,
    )

    return report
