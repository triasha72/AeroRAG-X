"""Tests for the manually verified multimodal report evaluation slice."""

from pathlib import Path

from aeroragx.processing.multimodal_provenance import (
    load_visual_asset_records,
    validate_visual_asset_provenance,
)
from aeroragx.processing.pdf import PDFPageRecord

DOCUMENT_ID = 20050228985
DOCUMENT_SHA256 = (
    "38ffad19c7c2d61858a97ccc8c225d35254b63808140365b213382d2af3c5d6b"
)
SOURCE_PATH = "data/raw/ntrs/v0_1/20050228985.pdf"
SOURCE_URL = (
    "https://ntrs.nasa.gov/api/citations/20050228985/"
    "downloads/20050228985.pdf"
)
CITATION_URL = "https://ntrs.nasa.gov/citations/20050228985"
SLICE_PATH = Path("data/evaluation/multimodal_report_slice_v0_1.jsonl")


def make_page(page_number: int) -> PDFPageRecord:
    """Create canonical provenance for one selected page."""

    return PDFPageRecord(
        page_id=f"{DOCUMENT_ID}:page:{page_number}",
        document_id=DOCUMENT_ID,
        page_number=page_number,
        text="Page text.",
        character_count=10,
        extraction_status="ok",
        source_path=SOURCE_PATH,
        source_url=SOURCE_URL,
        citation_url=CITATION_URL,
        document_sha256=DOCUMENT_SHA256,
    )


def test_slice_contains_the_five_manually_verified_assets() -> None:
    assets = load_visual_asset_records(SLICE_PATH)

    assert [(asset.page_id, asset.asset_type, asset.asset_index) for asset in assets] == [
        ("20050228985:page:60", "figure", 0),
        ("20050228985:page:60", "figure", 1),
        ("20050228985:page:61", "figure", 0),
        ("20050228985:page:84", "figure", 0),
        ("20050228985:page:84", "table", 0),
    ]


def test_slice_preserves_selected_page_provenance() -> None:
    assets = load_visual_asset_records(SLICE_PATH)
    validate_visual_asset_provenance(assets, [make_page(60), make_page(61), make_page(84)])
    assert {asset.document_sha256 for asset in assets} == {DOCUMENT_SHA256}


def test_page_101_is_a_documented_negative_control_not_an_asset() -> None:
    assets = load_visual_asset_records(SLICE_PATH)
    assert "20050228985:page:101" not in {asset.page_id for asset in assets}
    assert assets[-1].caption_text is None
