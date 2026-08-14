"""Build deterministic JSONL manifests for rendered multimodal report pages."""

import json
from collections.abc import Sequence
from pathlib import Path

from aeroragx.processing.multimodal_page_rendering import (
    PageRenderRecord,
    render_visual_asset_pages,
)
from aeroragx.processing.multimodal_provenance import load_visual_asset_records


def load_page_render_records(path: Path) -> list[PageRenderRecord]:
    """Load page-render records from a deterministic JSON Lines manifest."""

    records: list[PageRenderRecord] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            record = PageRenderRecord.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid page-render record on line {line_number}: {exc}") from exc

        records.append(record)

    _revalidate_unique_page_render_records(records)

    return records


def write_page_render_records(
    path: Path,
    records: Sequence[PageRenderRecord],
) -> None:
    """Write one deterministic page-render record per rendered PDF page."""

    validated_records = _revalidate_unique_page_render_records(records)
    ordered_records = sorted(
        validated_records,
        key=lambda record: (
            record.document_id,
            record.page_number,
            record.page_id,
        ),
    )
    rows = [
        json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
        )
        for record in ordered_records
    ]
    content = "\n".join(rows)

    if content:
        content += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render_visual_asset_manifest(
    assets_input_path: Path,
    output_directory: Path,
    manifest_output_path: Path,
    dpi: int = 144,
) -> list[PageRenderRecord]:
    """Render pages referenced by a visual-asset JSONL file and persist a manifest.

    Source-PDF checksum validation, source-page selection, and PNG generation are
    delegated to :func:`render_visual_asset_pages`. The manifest is written only
    after all requested pages render successfully.
    """

    assets = load_visual_asset_records(assets_input_path)
    records = render_visual_asset_pages(
        assets,
        output_directory=output_directory,
        dpi=dpi,
    )
    write_page_render_records(manifest_output_path, records)

    return records


def _revalidate_unique_page_render_records(
    records: Sequence[PageRenderRecord],
) -> list[PageRenderRecord]:
    """Revalidate records and reject ambiguous manifest identities."""

    validated_records: list[PageRenderRecord] = []
    page_ids: set[str] = set()
    png_paths: set[str] = set()

    for record in records:
        validated_record = PageRenderRecord.model_validate(record.model_dump(mode="python"))

        if validated_record.page_id in page_ids:
            raise ValueError(f"Duplicate page-render page ID: {validated_record.page_id}.")

        if validated_record.png_path in png_paths:
            raise ValueError(f"Duplicate page-render PNG path: {validated_record.png_path}.")

        page_ids.add(validated_record.page_id)
        png_paths.add(validated_record.png_path)
        validated_records.append(validated_record)

    return validated_records
