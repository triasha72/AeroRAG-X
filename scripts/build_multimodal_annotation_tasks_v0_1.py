"""Build deterministic v0.1 multimodal annotation tasks from visual-asset records."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.evaluation.multimodal_annotation import (
    build_multimodal_annotation_tasks,
    write_multimodal_annotation_tasks,
)
from aeroragx.processing.multimodal_provenance import load_visual_asset_records


def parse_arguments() -> argparse.Namespace:
    """Parse the versioned visual-asset input and annotation-task output paths."""

    parser = argparse.ArgumentParser(
        description=(
            "Build page-linked review tasks from the validated v0.1 multimodal report slice."
        )
    )
    parser.add_argument(
        "--assets-input",
        type=Path,
        default=Path("data/evaluation/multimodal_report_slice_v0_1.jsonl"),
        help="Validated visual-asset JSONL input path.",
    )
    parser.add_argument(
        "--tasks-output",
        type=Path,
        default=Path("data/evaluation/multimodal_annotation_tasks_v0_1.jsonl"),
        help="Deterministic annotation-task JSONL output path.",
    )

    return parser.parse_args()


def main() -> None:
    """Build and write one review task for each validated visual-asset record."""

    arguments = parse_arguments()
    assets = load_visual_asset_records(arguments.assets_input)
    tasks = build_multimodal_annotation_tasks(assets)
    write_multimodal_annotation_tasks(arguments.tasks_output, tasks)

    print(f"Wrote {len(tasks)} multimodal annotation tasks.")
    print(f"Annotation-task JSONL: {arguments.tasks_output}")


if __name__ == "__main__":
    main()
