"""Cross-platform rendering for pages linked to validated multimodal assets."""

from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal, Self

import pypdfium2
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator

from aeroragx.ingestion.acquisition import sha256_file
from aeroragx.processing.multimodal_provenance import VisualAssetRecord

_PDF_POINTS_PER_INCH = 72
_RENDERER_NAME: Literal["pypdfium2"] = "pypdfium2"
_SHARED_PAGE_PROVENANCE_FIELDS = (
    "document_id",
    "page_number",
    "source_path",
    "source_url",
    "citation_url",
    "document_sha256",
)


class PageRenderRecord(BaseModel):
    """Provenance and properties for one rendered PDF page PNG."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    page_id: str = Field(min_length=1)
    document_id: int
    page_number: int = Field(ge=1)
    source_path: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    citation_url: str = Field(min_length=1)
    document_sha256: str = Field(min_length=1)
    png_path: str = Field(min_length=1)
    png_sha256: str = Field(min_length=1)
    width_pixels: int = Field(ge=1)
    height_pixels: int = Field(ge=1)
    dpi: int = Field(ge=1)
    renderer_name: Literal["pypdfium2"]
    renderer_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        """Ensure the rendered page keeps the deterministic PDF page identifier."""

        expected_page_id = f"{self.document_id}:page:{self.page_number}"

        if self.page_id != expected_page_id:
            raise ValueError(
                f"page_id must equal '{expected_page_id}' for document_id and page_number."
            )

        if Path(self.png_path).suffix.lower() != ".png":
            raise ValueError("png_path must point to a PNG file.")

        return self


def build_page_render_path(
    output_directory: Path,
    document_id: int,
    page_number: int,
) -> Path:
    """Return the deterministic output path for one rendered PDF page."""

    return output_directory / str(document_id) / f"page_{page_number:04d}.png"


def render_visual_asset_pages(
    assets: Sequence[VisualAssetRecord],
    output_directory: Path,
    dpi: int = 144,
) -> list[PageRenderRecord]:
    """Render each unique page referenced by validated visual-asset records.

    The function deliberately renders whole pages only. It does not infer figure or
    table boundaries, crop assets, perform OCR, or create embeddings.
    """

    if dpi < 1:
        raise ValueError("DPI must be at least 1.")

    page_assets = _select_unique_page_assets(assets)

    return [
        _render_page(
            asset=asset,
            output_directory=output_directory,
            dpi=dpi,
        )
        for asset in page_assets
    ]


def _select_unique_page_assets(
    assets: Sequence[VisualAssetRecord],
) -> list[VisualAssetRecord]:
    """Revalidate assets and return one representative record per source page."""

    assets_by_page_id: dict[str, VisualAssetRecord] = {}
    seen_asset_ids: set[str] = set()

    for asset in assets:
        validated_asset = VisualAssetRecord.model_validate(asset.model_dump(mode="python"))

        if validated_asset.asset_id in seen_asset_ids:
            raise ValueError(f"Duplicate visual asset ID: {validated_asset.asset_id}.")

        seen_asset_ids.add(validated_asset.asset_id)

        existing_asset = assets_by_page_id.get(validated_asset.page_id)

        if existing_asset is None:
            assets_by_page_id[validated_asset.page_id] = validated_asset
            continue

        _validate_shared_page_provenance(
            existing_asset,
            validated_asset,
        )

    return sorted(
        assets_by_page_id.values(),
        key=lambda asset: (asset.document_id, asset.page_number),
    )


def _validate_shared_page_provenance(
    existing_asset: VisualAssetRecord,
    candidate_asset: VisualAssetRecord,
) -> None:
    """Reject contradictory records that point to the same source page."""

    for field_name in _SHARED_PAGE_PROVENANCE_FIELDS:
        existing_value = getattr(existing_asset, field_name)
        candidate_value = getattr(candidate_asset, field_name)

        if existing_value != candidate_value:
            raise ValueError(
                f"Visual assets for page {existing_asset.page_id} disagree on {field_name}."
            )


def _render_page(
    asset: VisualAssetRecord,
    output_directory: Path,
    dpi: int,
) -> PageRenderRecord:
    """Verify and render one source PDF page as a PNG."""

    source_path = _verify_source_pdf(asset)
    png_path = build_page_render_path(
        output_directory,
        asset.document_id,
        asset.page_number,
    )

    with pypdfium2.PdfDocument(source_path) as document:
        if asset.page_number > len(document):
            raise ValueError(f"Document {asset.document_id} has no page {asset.page_number}.")

        page = document[asset.page_number - 1]

        try:
            bitmap = page.render(scale=dpi / _PDF_POINTS_PER_INCH)

            try:
                image: Image.Image = bitmap.to_pil()
                width_pixels, height_pixels = image.size
                png_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    image.save(
                        png_path,
                        format="PNG",
                        dpi=(dpi, dpi),
                    )
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()

    return PageRenderRecord(
        page_id=asset.page_id,
        document_id=asset.document_id,
        page_number=asset.page_number,
        source_path=asset.source_path,
        source_url=asset.source_url,
        citation_url=asset.citation_url,
        document_sha256=asset.document_sha256,
        png_path=str(png_path),
        png_sha256=sha256_file(png_path),
        width_pixels=width_pixels,
        height_pixels=height_pixels,
        dpi=dpi,
        renderer_name=_RENDERER_NAME,
        renderer_version=_renderer_version(),
    )


def _verify_source_pdf(
    asset: VisualAssetRecord,
) -> Path:
    """Verify a source PDF exists and matches its visual-asset checksum."""

    source_path = Path(asset.source_path)

    if not source_path.is_file():
        raise ValueError(f"PDF does not exist: {source_path}")

    actual_checksum = sha256_file(source_path)

    if actual_checksum != asset.document_sha256:
        raise ValueError(f"Checksum mismatch for document {asset.document_id}.")

    return source_path


def _renderer_version() -> str:
    """Return the installed pypdfium2 distribution version."""

    try:
        return version(_RENDERER_NAME)
    except PackageNotFoundError as exc:
        raise RuntimeError("pypdfium2 must be installed to render PDF pages.") from exc
