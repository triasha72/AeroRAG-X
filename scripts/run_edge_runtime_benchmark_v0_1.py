"""Run the AeroRAG-X v0.1 local edge-runtime benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.generation.edge_runtime_runner import (
    run_edge_runtime_benchmark,
)


def parse_arguments() -> argparse.Namespace:
    """Parse benchmark configuration and output locations."""

    parser = argparse.ArgumentParser(
        description=(
            "Measure local Qwen runtime performance across CPU, MPS, "
            "precision, and LoRA configurations."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/edge_runtime_benchmark_v0_1.yaml"),
        help="Benchmark YAML configuration path.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=Path("reports/edge_runtime_benchmark_v0_1.json"),
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        type=Path,
        default=Path("reports/edge_runtime_benchmark_v0_1.md"),
        help="Markdown report output path.",
    )

    return parser.parse_args()


def main() -> None:
    """Run benchmark cases and print a concise results summary."""

    arguments = parse_arguments()

    report = run_edge_runtime_benchmark(
        config_path=str(arguments.config),
        json_report_path=str(arguments.json_report),
        markdown_report_path=str(arguments.markdown_report),
    )

    print(f"Completed edge runtime benchmark v{report.version}")
    print(f"Model: {report.model_name}")
    print(f"JSON report: {arguments.json_report}")
    print(f"Markdown report: {arguments.markdown_report}")
    print()

    for summary in report.case_summaries:
        throughput = (
            "n/a"
            if summary.output_tokens_per_second is None
            else f"{summary.output_tokens_per_second:.2f}"
        )
        adapter = "LoRA" if summary.adapter_path is not None else "Base"

        print(
            f"{summary.case_name}: "
            f"{summary.mean_latency_ms:.2f} ms mean, "
            f"{throughput} output tok/s, "
            f"{summary.device}/{summary.dtype}/{adapter}"
        )


if __name__ == "__main__":
    main()
