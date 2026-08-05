"""Download NTRS documents and generate integrity receipts."""

import hashlib
import json
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

from aeroragx.ingestion.corpus import ManifestEntry


class DownloadReceipt(BaseModel):
    """Result of acquiring one NASA document."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: int
    source_url: str
    local_path: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    status: Literal["downloaded", "skipped", "failed"]
    error: str | None = None


def load_manifest(path: Path) -> list[ManifestEntry]:
    """Load a JSONL NTRS manifest."""

    entries: list[ManifestEntry] = []

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            entry = ManifestEntry.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid manifest row {line_number}: {exc}") from exc

        entries.append(entry)

    return entries


def sha256_file(path: Path) -> str:
    """Calculate the SHA-256 digest of a local file."""

    digest = hashlib.sha256()

    with path.open("rb") as file_stream:
        while chunk := file_stream.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def is_pdf(path: Path) -> bool:
    """Check whether a file begins with the PDF signature."""

    with path.open("rb") as file_stream:
        return file_stream.read(5) == b"%PDF-"


def download_documents(
    entries: list[ManifestEntry],
    output_dir: Path,
    limit: int | None = None,
    timeout_seconds: float = 60.0,
    overwrite: bool = False,
    transport: httpx.BaseTransport | None = None,
) -> list[DownloadReceipt]:
    """Download available PDFs and return integrity receipts."""

    if limit is not None and limit < 1:
        raise ValueError("Limit must be at least 1.")

    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = [entry for entry in entries if entry.pdf_url is not None]

    if limit is not None:
        candidates = candidates[:limit]

    receipts: list[DownloadReceipt] = []

    with httpx.Client(
        timeout=timeout_seconds,
        transport=transport,
        follow_redirects=True,
        headers={"User-Agent": "AeroRAG-X/0.1"},
    ) as client:
        for entry in candidates:
            source_url = entry.pdf_url

            if source_url is None:
                continue

            target_path = output_dir / f"{entry.document_id}.pdf"
            temporary_path = output_dir / f"{entry.document_id}.pdf.part"

            if target_path.exists() and not overwrite:
                receipts.append(
                    DownloadReceipt(
                        document_id=entry.document_id,
                        source_url=source_url,
                        local_path=str(target_path),
                        sha256=sha256_file(target_path),
                        size_bytes=target_path.stat().st_size,
                        status="skipped",
                    )
                )
                continue

            try:
                with client.stream("GET", source_url) as response:
                    response.raise_for_status()

                    with temporary_path.open("wb") as output_stream:
                        for chunk in response.iter_bytes():
                            output_stream.write(chunk)

                if not is_pdf(temporary_path):
                    raise ValueError("Downloaded file does not have a PDF signature.")

                temporary_path.replace(target_path)

                receipts.append(
                    DownloadReceipt(
                        document_id=entry.document_id,
                        source_url=source_url,
                        local_path=str(target_path),
                        sha256=sha256_file(target_path),
                        size_bytes=target_path.stat().st_size,
                        status="downloaded",
                    )
                )

            except (httpx.HTTPError, OSError, ValueError) as exc:
                temporary_path.unlink(missing_ok=True)

                receipts.append(
                    DownloadReceipt(
                        document_id=entry.document_id,
                        source_url=source_url,
                        status="failed",
                        error=str(exc),
                    )
                )

    return receipts


def write_download_receipts(
    path: Path,
    receipts: list[DownloadReceipt],
) -> None:
    """Write download receipts using JSON Lines format."""

    path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        json.dumps(
            receipt.model_dump(mode="json"),
            sort_keys=True,
        )
        for receipt in receipts
    ]

    content = "\n".join(rows)

    if content:
        content += "\n"

    path.write_text(content, encoding="utf-8")
