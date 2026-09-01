"""Build a resumable, real NASA NTRS corpus for retrieval-scale measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import urljoin

import httpx
import yaml
from pypdf import PdfReader

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.processing.pdf import normalize_page_text

NTRS = "https://ntrs.nasa.gov"
logging.getLogger("pypdf").setLevel(logging.ERROR)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/corpus_v0_1.yaml"))
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--target-chunks", type=int, default=10_000)
    parser.add_argument("--records-per-query", type=int, default=250)
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--query", action="append", dest="queries")
    parser.add_argument("--delete-pdfs", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--request-retries", type=int, default=4)
    return parser.parse_args()


def _download(record: dict[str, object]) -> tuple[str, str] | None:
    downloads = record.get("downloads")
    if not isinstance(downloads, list):
        return None
    for item in downloads:
        if not isinstance(item, dict) or item.get("mimetype") != "application/pdf":
            continue
        links = item.get("links")
        if isinstance(links, dict) and isinstance(links.get("pdf"), str):
            return str(item.get("name") or "report.pdf"), urljoin(NTRS, links["pdf"])
    return None


def _year(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"^(\d{4})", value)
    return int(match.group(1)) if match else None


def _strings(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _get_with_retries(
    client: httpx.Client,
    url: str,
    *,
    retries: int,
    params: dict[str, object] | None = None,
) -> httpx.Response:
    for attempt in range(retries + 1):
        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response
        except (httpx.HTTPError, httpx.TimeoutException):
            if attempt == retries:
                raise
            time.sleep(min(2**attempt, 8))
    raise RuntimeError("unreachable")


def iter_search_records(
    client: httpx.Client,
    queries: list[str],
    size: int,
    page_size: int,
    retries: int,
) -> Iterator[dict[str, object]]:
    seen: set[int] = set()
    for query in queries:
        for offset in range(0, size, page_size):
            response = _get_with_retries(
                client,
                "/api/citations/search",
                retries=retries,
                params={
                    "q": query,
                    "page.size": min(page_size, size - offset),
                    "page.from": offset,
                },
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
            for item in results:
                if isinstance(item, dict) and isinstance(item.get("id"), int):
                    document_id = int(item["id"])
                    if document_id not in seen:
                        seen.add(document_id)
                        yield item
            if len(results) < min(page_size, size - offset):
                break


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return sum(1 for line in handle if line.strip())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def chunk_pdf(
    *,
    pdf_path: Path,
    record: dict[str, object],
    source_url: str,
    checksum: str,
    chunk_words: int,
    overlap_words: int,
) -> list[ChunkRecord]:
    document_id = int(record["id"])
    words: list[tuple[str, int]] = []
    for page_number, page in enumerate(PdfReader(str(pdf_path), strict=False).pages, 1):
        text = normalize_page_text(page.extract_text() or "")
        words.extend((word, page_number) for word in text.split())
    chunks: list[ChunkRecord] = []
    step = chunk_words - overlap_words
    for chunk_index, start in enumerate(range(0, len(words), step)):
        window = words[start : start + chunk_words]
        if not window:
            continue
        text = " ".join(word for word, _ in window)
        pages = sorted({page for _, page in window})
        funding = record.get("fundingNumbers")
        programs = [
            str(item.get("number"))
            for item in funding
            if isinstance(item, dict) and item.get("number")
        ] if isinstance(funding, list) else []
        chunks.append(
            ChunkRecord(
                chunk_id=f"{document_id}:chunk:{chunk_index:05d}",
                document_id=document_id,
                chunk_index=chunk_index,
                page_start=pages[0],
                page_end=pages[-1],
                page_ids=[f"{document_id}:page:{page}" for page in pages],
                text=text,
                word_count=len(window),
                character_count=len(text),
                token_estimate=max(1, len(text) // 4),
                citation_url=f"{NTRS}/citations/{document_id}",
                source_url=source_url,
                document_sha256=checksum,
                title=str(record.get("title") or "") or None,
                publication_year=_year(record.get("distributionDate")),
                subject_categories=_strings(record.get("subjectCategories")),
                document_type=str(record.get("stiType") or "") or None,
                programs=programs,
                report_family=str(record.get("center", {}).get("code") or "")
                if isinstance(record.get("center"), dict)
                else None,
            )
        )
        if start + chunk_words >= len(words):
            break
    return chunks


def main() -> None:
    args = parse_arguments()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    queries = args.queries or [str(item) for item in config["queries"]]
    chunk_config = yaml.safe_load(Path("configs/chunking_v0_1.yaml").read_text(encoding="utf-8"))
    output = args.output_directory
    pdf_directory = output / "pdfs"
    pdf_directory.mkdir(parents=True, exist_ok=True)
    chunks_path = output / "chunks.jsonl"
    receipts_path = output / "receipts.jsonl"
    completed = {
        int(json.loads(line)["document_id"])
        for line in receipts_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    } if receipts_path.exists() else set()
    existing_count = _line_count(chunks_path)

    with httpx.Client(base_url=NTRS, timeout=args.timeout_seconds, follow_redirects=True) as client:
        with chunks_path.open("a", encoding="utf-8") as chunk_file, receipts_path.open("a", encoding="utf-8") as receipt_file:
            for record in iter_search_records(
                client,
                queries,
                args.records_per_query,
                args.page_size,
                args.request_retries,
            ):
                document_id = int(record["id"])
                if document_id in completed or existing_count >= args.target_chunks:
                    continue
                download = _download(record)
                if download is None:
                    continue
                filename, source_url = download
                pdf_path = pdf_directory / f"{document_id}_{Path(filename).name}"
                if not pdf_path.exists():
                    response = _get_with_retries(
                        client,
                        source_url,
                        retries=args.request_retries,
                    )
                    pdf_path.write_bytes(response.content)
                checksum = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
                try:
                    chunks = chunk_pdf(
                        pdf_path=pdf_path,
                        record=record,
                        source_url=source_url,
                        checksum=checksum,
                        chunk_words=int(chunk_config["chunk_words"]),
                        overlap_words=int(chunk_config["overlap_words"]),
                    )
                except Exception as error:
                    receipt_file.write(json.dumps({"document_id": document_id, "status": "failed", "error": str(error)}, sort_keys=True) + "\n")
                    receipt_file.flush()
                    continue
                for chunk in chunks:
                    chunk_file.write(chunk.model_dump_json() + "\n")
                chunk_file.flush()
                receipt_file.write(json.dumps({"document_id": document_id, "status": "processed", "chunks": len(chunks), "sha256": checksum}, sort_keys=True) + "\n")
                receipt_file.flush()
                existing_count += len(chunks)
                print(f"document={document_id} chunks={len(chunks)} total={existing_count}")
                if args.delete_pdfs:
                    pdf_path.unlink(missing_ok=True)

    manifest = {
        "version": "0.1",
        "source": "NASA NTRS PDFs",
        "chunk_count": existing_count,
        "target_chunk_count": args.target_chunks,
        "complete": existing_count >= args.target_chunks,
        "chunks_sha256": _sha256(chunks_path),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
