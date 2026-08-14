"""Render the v0.1 multimodal report slice and write its page manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from aeroragx.processing.multimodal_render_manifest import (
    render_visual_asset_manifest,
)


def parse_arguments() -> argparse.Namespace:
    """Parse source-slice, output, and rendering options."""

    parser = argparse.ArgumentParser(
        description=("Render only PDF pages linked to the validated v0.1 multimodal report slice.")
    )
    parser.add_argument(
        "--assets-input",
        type=Path,
        default=Path("data/evaluation/multimodal_report_slice_v0_1.jsonl"),
        help="Visual-asset JSONL input path.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/derived/multimodal/page_renders"),
        help="Directory for derived page PNGs.",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=Path(
            "data/derived/multimodal/page_renders/multimodal_report_slice_v0_1_page_renders.jsonl"
        ),
        help="Derived PageRenderRecord JSONL output path.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=144,
        help="Rendering resolution in dots per inch.",
    )

    return parser.parse_args()


def main() -> None:
    """Render the configured source pages and print their local output locations."""

    arguments = parse_arguments()
    records = render_visual_asset_manifest(
        assets_input_path=arguments.assets_input,
        output_directory=arguments.output_directory,
        manifest_output_path=arguments.manifest_output,
        dpi=arguments.dpi,
    )

    print(f"Rendered {len(records)} unique PDF pages.")
    print(f"Page-render manifest: {arguments.manifest_output}")
    print(f"PNG output directory: {arguments.output_directory}")


if __name__ == "__main__":
    main()
