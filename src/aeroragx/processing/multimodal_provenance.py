"""Page-linked provenance records for future multimodal report assets."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.processing.pdf import PDFPageRecord

VisualAssetType = Literal["figure", "table"]


def build_visual_asset_id(
    page_id: str,
    asset_type: VisualAssetType,
    asset_index: int,
) -> str:
    """Return the deterministic identifier for one page-linked visual asset."""

    return f"{page_id}:{asset_type}:{asset_index:03d}"


class VisualAssetRecord(BaseModel):
    """Provenance contract for one future figure or table asset."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    asset_id: str = Field(min_length=1)
    document_id: int
    page_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    asset_type: VisualAssetType
    asset_index: int = Field(ge=0)
    caption_text: str | None = None
    source_path: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    citation_url: str = Field(min_length=1)
    document_sha256: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        """Ensure page and asset identifiers are deterministic."""

        expected_page_id = f"{self.document_id}:page:{self.page_number}"

        if self.page_id != expected_page_id:
            raise ValueError(
                f"page_id must equal '{expected_page_id}' for document_id and page_number."
            )

        expected_asset_id = build_visual_asset_id(
            self.page_id,
            self.asset_type,
            self.asset_index,
        )

        if self.asset_id != expected_asset_id:
            raise ValueError(
                "asset_id must equal "
                f"'{expected_asset_id}' for page_id, asset_type, and asset_index."
            )

        return self


def validate_visual_asset_provenance(
    assets: Sequence[VisualAssetRecord],
    pages: Sequence[PDFPageRecord],
) -> None:
    """Ensure assets link to existing pages with identical provenance."""

    _validate_unique_asset_ids(assets)

    pages_by_id: dict[str, PDFPageRecord] = {}

    for page in pages:
        if page.page_id in pages_by_id:
            raise ValueError(f"Duplicate PDF page ID: {page.page_id}.")

        pages_by_id[page.page_id] = page

    for asset in assets:
        linked_page = pages_by_id.get(asset.page_id)

        if linked_page is None:
            raise ValueError(f"Unknown page ID for visual asset {asset.asset_id}: {asset.page_id}.")

        comparisons = (
            ("document_id", asset.document_id, linked_page.document_id),
            ("page_number", asset.page_number, linked_page.page_number),
            ("source_path", asset.source_path, linked_page.source_path),
            ("source_url", asset.source_url, linked_page.source_url),
            ("citation_url", asset.citation_url, linked_page.citation_url),
            (
                "document_sha256",
                asset.document_sha256,
                linked_page.document_sha256,
            ),
        )

        for field_name, asset_value, page_value in comparisons:
            if asset_value != page_value:
                raise ValueError(
                    f"Visual asset {asset.asset_id} does not match PDF page "
                    f"{asset.page_id} for {field_name}."
                )


def load_visual_asset_records(
    path: Path,
) -> list[VisualAssetRecord]:
    """Load visual-asset records from a JSONL file."""

    records: list[VisualAssetRecord] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            record = VisualAssetRecord.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid visual-asset record on line {line_number}: {exc}") from exc

        records.append(record)

    _validate_unique_asset_ids(records)

    return records


def write_visual_asset_records(
    path: Path,
    assets: Sequence[VisualAssetRecord],
) -> None:
    """Write visual-asset records as deterministic JSON Lines."""

    _validate_unique_asset_ids(assets)

    ordered_assets = sorted(
        assets,
        key=lambda asset: (
            asset.document_id,
            asset.page_number,
            asset.asset_type,
            asset.asset_index,
        ),
    )

    rows = [
        json.dumps(
            asset.model_dump(mode="json"),
            sort_keys=True,
        )
        for asset in ordered_assets
    ]

    content = "\n".join(rows)

    if content:
        content += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _validate_unique_asset_ids(
    assets: Sequence[VisualAssetRecord],
) -> None:
    """Reject duplicate visual-asset identifiers."""

    seen_asset_ids: set[str] = set()

    for asset in assets:
        if asset.asset_id in seen_asset_ids:
            raise ValueError(f"Duplicate visual asset ID: {asset.asset_id}.")

        seen_asset_ids.add(asset.asset_id)
