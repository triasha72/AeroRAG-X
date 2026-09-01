"""Rebuild the checksum-pinned NTRS v0.1 pages and chunks fail-closed."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from aeroragx.processing.chunking import (
    build_chunks,
    load_chunking_config,
    write_chunk_records,
)
from aeroragx.processing.pdf import (
    load_download_receipts,
    process_downloaded_pdfs,
    write_page_records,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_MANIFEST = REPO_ROOT / "data/manifests/ntrs_v0_1_downloads.jsonl"
EXTRACTION_MANIFEST = REPO_ROOT / "data/manifests/ntrs_v0_1_extraction.jsonl"
CHUNKING_MANIFEST = REPO_ROOT / "data/manifests/ntrs_v0_1_chunking.jsonl"
CHUNKING_CONFIG = REPO_ROOT / "configs/chunking_v0_1.yaml"
PAGES_OUTPUT = REPO_ROOT / "data/processed/ntrs/v0_1/pages.jsonl"
CHUNKS_OUTPUT = REPO_ROOT / "data/processed/ntrs/v0_1/chunks.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load one JSONL file."""

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_download(*, source_url: str, destination: Path, expected_sha256: str) -> None:
    """Download one missing PDF and require its frozen checksum."""

    if destination.exists() and sha256_file(destination) == expected_sha256:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")

    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(
                source_url,
                headers={"User-Agent": "AeroRAG-X frozen-corpus rebuild/0.1"},
            )
            with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:
                while block := response.read(1024 * 1024):
                    out.write(block)

            actual_sha256 = sha256_file(partial)
            if actual_sha256 != expected_sha256:
                raise RuntimeError(
                    f"Checksum mismatch for {destination.name}: "
                    f"{actual_sha256} != {expected_sha256}"
                )

            partial.replace(destination)
            return
        except Exception:
            if partial.exists():
                partial.unlink()
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def main() -> None:
    """Restore and validate the exact frozen v0.1 retrieval corpus."""

    expected_extraction = load_jsonl(EXTRACTION_MANIFEST)
    expected_chunking = load_jsonl(CHUNKING_MANIFEST)
    processed_ids = {
        int(row["document_id"]) for row in expected_extraction if row["status"] == "processed"
    }
    receipts = [
        receipt
        for receipt in load_download_receipts(DOWNLOAD_MANIFEST)
        if receipt.document_id in processed_ids
    ]

    if len(receipts) != len(processed_ids):
        raise RuntimeError(
            f"Frozen receipt coverage mismatch: {len(receipts)} != {len(processed_ids)}"
        )

    for position, receipt in enumerate(receipts, start=1):
        if receipt.local_path is None or receipt.sha256 is None:
            raise RuntimeError(f"Incomplete frozen receipt for {receipt.document_id}")
        print(f"pdf={position}/{len(receipts)} document={receipt.document_id}", flush=True)
        ensure_download(
            source_url=receipt.source_url,
            destination=REPO_ROOT / receipt.local_path,
            expected_sha256=receipt.sha256,
        )

    pages, extraction_receipts = process_downloaded_pdfs(receipts=receipts)
    actual_extraction = [receipt.model_dump(mode="json") for receipt in extraction_receipts]
    if actual_extraction != expected_extraction:
        raise RuntimeError("Rebuilt extraction receipts do not match the frozen manifest.")

    chunks, chunking_receipts = build_chunks(
        pages=pages,
        config=load_chunking_config(CHUNKING_CONFIG),
    )
    actual_chunking = [receipt.model_dump(mode="json") for receipt in chunking_receipts]
    if actual_chunking != expected_chunking:
        raise RuntimeError("Rebuilt chunking receipts do not match the frozen manifest.")

    if len(chunks) != 3233:
        raise RuntimeError(f"Expected 3,233 chunks, rebuilt {len(chunks)}.")

    write_page_records(path=PAGES_OUTPUT, pages=pages)
    write_chunk_records(path=CHUNKS_OUTPUT, chunks=chunks)

    print(f"pages={len(pages)}", flush=True)
    print(f"chunks={len(chunks)}", flush=True)
    print(f"chunks_sha256={sha256_file(CHUNKS_OUTPUT)}", flush=True)
    print("FROZEN NTRS V0.1 CORPUS REBUILD: PASS", flush=True)


if __name__ == "__main__":
    main()
