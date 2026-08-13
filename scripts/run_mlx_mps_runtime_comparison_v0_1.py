"""Run the controlled AeroRAG-X MLX 4-bit versus MPS float16 comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.generation.mlx_mps_runtime_comparison import (
    run_mlx_mps_runtime_comparison,
)


def parse_arguments() -> argparse.Namespace:
    """Parse the fixed-workload config and versioned report destinations."""

    parser = argparse.ArgumentParser(
        description=(
            "Compare local Transformers MPS float16 against local MLX affine 4-bit "
            "Qwen structured generation under one controlled workload."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/mlx_mps_runtime_comparison_v0_1.yaml"),
        help="Comparison YAML configuration path.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=Path("reports/mlx_mps_runtime_comparison_v0_1.json"),
        help="JSON report output path.",
    )
    parser.add_argument(
        "--markdown-report",
        type=Path,
        default=Path("reports/mlx_mps_runtime_comparison_v0_1.md"),
        help="Markdown report output path.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the comparison and print concise artifact locations."""

    arguments = parse_arguments()
    report = run_mlx_mps_runtime_comparison(
        config_path=str(arguments.config),
        json_report_path=str(arguments.json_report),
        markdown_report_path=str(arguments.markdown_report),
    )

    print(f"Completed MLX/MPS comparison v{report.version}")
    print(f"Source model: {report.source_model_name}")
    print(f"JSON report: {arguments.json_report}")
    print(f"Markdown report: {arguments.markdown_report}")


if __name__ == "__main__":
    main()
