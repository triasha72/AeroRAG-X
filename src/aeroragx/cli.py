"""Command-line interface for AeroRAG-X."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from aeroragx import __version__
from aeroragx.config import load_config
from aeroragx.evaluation.retrieval import (
    build_bm25_candidates,
    evaluate_bm25,
    load_evaluation_queries,
    load_relevance_judgments,
    write_candidate_records,
    write_evaluation_report,
)
from aeroragx.ingestion.acquisition import (
    download_documents,
    load_manifest,
    write_download_receipts,
)
from aeroragx.ingestion.corpus import (
    build_manifest,
    load_corpus_definition,
    write_manifest,
)
from aeroragx.ingestion.ntrs import (
    NTRSClient,
    records_to_json_rows,
)
from aeroragx.processing.chunking import (
    build_chunks,
    load_chunking_config,
    load_page_records,
    write_chunk_records,
    write_chunking_receipts,
)
from aeroragx.processing.pdf import (
    load_download_receipts,
    process_downloaded_pdfs,
    write_extraction_receipts,
    write_page_records,
)
from aeroragx.retrieval.bm25 import (
    BM25Index,
    load_bm25_config,
    load_chunk_records,
    write_search_results,
)

app = typer.Typer(
    no_args_is_help=True,
    help="AeroRAG-X development CLI.",
)
console = Console()


@app.command()
def info() -> None:
    """Show the installed project version."""
    console.print(f"AeroRAG-X {__version__}")


@app.command(name="validate-config")
def validate_config(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", exists=True, dir_okay=False, readable=True),
    ] = Path("configs/base.yaml"),
) -> None:
    """Validate the project YAML configuration."""
    settings = load_config(config)
    console.print(f"Configuration valid: [bold]{settings.project_name}[/bold]")
    console.print(f"Data directory: {settings.data_dir}")
    console.print(f"NTRS endpoint: {settings.ntrs.base_url}")


@app.command(name="ntrs-search")
def ntrs_search(
    title: Annotated[str, typer.Option("--title", "-t", help="Title text to search.")],
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, max=100)] = 5,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", dir_okay=False, help="Optional JSON output path."),
    ] = None,
    config: Annotated[
        Path,
        typer.Option("--config", "-c", exists=True, dir_okay=False, readable=True),
    ] = Path("configs/base.yaml"),
) -> None:
    """Search NASA NTRS public citation metadata by report title."""
    settings = load_config(config)
    with NTRSClient(
        base_url=settings.ntrs.base_url,
        timeout_seconds=settings.ntrs.timeout_seconds,
    ) as client:
        records = client.search_by_title(title=title, limit=limit)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(records_to_json_rows(records), indent=2),
            encoding="utf-8",
        )
        console.print(f"Saved {len(records)} records to {output}")
        return

    table = Table(title=f"NASA NTRS results: {title}")
    table.add_column("Document ID", style="bold")
    table.add_column("Title")
    table.add_column("PDF")
    for record in records:
        table.add_row(
            str(record.document_id),
            record.title,
            "yes" if record.downloads_available else "no/unknown",
        )
    console.print(table)


@app.command(name="ntrs-build-manifest")
def ntrs_build_manifest(
    corpus_config: Annotated[
        Path,
        typer.Option(
            "--corpus-config",
            exists=True,
            dir_okay=False,
            readable=True,
            help="YAML file defining the NTRS corpus.",
        ),
    ] = Path("configs/corpus_v0_1.yaml"),
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            dir_okay=False,
            help="JSONL manifest output path.",
        ),
    ] = Path("data/manifests/ntrs_v0_1.jsonl"),
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Base AeroRAG-X configuration.",
        ),
    ] = Path("configs/base.yaml"),
) -> None:
    """Build a deduplicated NASA NTRS metadata manifest."""

    settings = load_config(config)
    corpus_definition = load_corpus_definition(corpus_config)

    console.print(
        f"Building corpus: [bold]{corpus_definition.corpus_name}[/bold] "
        f"v{corpus_definition.version}"
    )
    console.print(f"Running {len(corpus_definition.queries)} search queries...")

    with NTRSClient(
        base_url=settings.ntrs.base_url,
        timeout_seconds=settings.ntrs.timeout_seconds,
    ) as client:
        entries = build_manifest(
            client=client,
            definition=corpus_definition,
        )

    write_manifest(
        path=output,
        entries=entries,
    )

    pdf_count = sum(entry.pdf_url is not None for entry in entries)
    fulltext_count = sum(entry.fulltext_url is not None for entry in entries)

    console.print()
    console.print(f"Saved [bold]{len(entries)}[/bold] unique records to {output}")
    console.print(f"Records with PDF links: {pdf_count}")
    console.print(f"Records with full-text links: {fulltext_count}")


@app.command(name="ntrs-download-documents")
def ntrs_download_documents(
    manifest: Annotated[
        Path,
        typer.Option(
            "--manifest",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Input NTRS JSONL manifest.",
        ),
    ] = Path("data/manifests/ntrs_v0_1.jsonl"),
    documents_dir: Annotated[
        Path,
        typer.Option(
            "--documents-dir",
            dir_okay=True,
            file_okay=False,
            help="Directory for downloaded PDF files.",
        ),
    ] = Path("data/raw/ntrs/v0_1"),
    receipts_output: Annotated[
        Path,
        typer.Option(
            "--receipts-output",
            dir_okay=False,
            help="Output JSONL download-receipt manifest.",
        ),
    ] = Path("data/manifests/ntrs_v0_1_downloads.jsonl"),
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum number of PDFs to process.",
        ),
    ] = 10,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Download files even when they already exist.",
        ),
    ] = False,
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/base.yaml"),
) -> None:
    """Download NTRS PDFs and generate checksum receipts."""

    settings = load_config(config)
    entries = load_manifest(manifest)

    console.print(f"Loaded [bold]{len(entries)}[/bold] manifest records.")
    console.print(f"Processing up to [bold]{limit}[/bold] downloadable PDFs...")

    receipts = download_documents(
        entries=entries,
        output_dir=documents_dir,
        limit=limit,
        timeout_seconds=settings.ntrs.timeout_seconds,
        overwrite=overwrite,
    )

    write_download_receipts(
        path=receipts_output,
        receipts=receipts,
    )

    downloaded_count = sum(receipt.status == "downloaded" for receipt in receipts)
    skipped_count = sum(receipt.status == "skipped" for receipt in receipts)
    failed_count = sum(receipt.status == "failed" for receipt in receipts)

    console.print()
    console.print(f"Downloaded: {downloaded_count}")
    console.print(f"Skipped: {skipped_count}")
    console.print(f"Failed: {failed_count}")
    console.print(f"Receipts: {receipts_output}")


@app.command(name="ntrs-extract-pages")
def ntrs_extract_pages(
    receipts_input: Annotated[
        Path,
        typer.Option(
            "--receipts-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/manifests/ntrs_v0_1_downloads.jsonl"),
    pages_output: Annotated[
        Path,
        typer.Option(
            "--pages-output",
            dir_okay=False,
        ),
    ] = Path("data/processed/ntrs/v0_1/pages.jsonl"),
    extraction_output: Annotated[
        Path,
        typer.Option(
            "--extraction-output",
            dir_okay=False,
        ),
    ] = Path("data/manifests/ntrs_v0_1_extraction.jsonl"),
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
        ),
    ] = 5,
    max_size_mb: Annotated[
        int,
        typer.Option(
            "--max-size-mb",
            min=1,
        ),
    ] = 20,
) -> None:
    """Extract page-level text from downloaded PDFs."""

    receipts = load_download_receipts(receipts_input)

    pages, extraction_receipts = process_downloaded_pdfs(
        receipts=receipts,
        limit=limit,
        max_size_bytes=(max_size_mb * 1024 * 1024),
    )

    write_page_records(
        path=pages_output,
        pages=pages,
    )
    write_extraction_receipts(
        path=extraction_output,
        receipts=extraction_receipts,
    )

    processed_count = sum(receipt.status == "processed" for receipt in extraction_receipts)
    failed_count = sum(receipt.status == "failed" for receipt in extraction_receipts)
    empty_page_count = sum(page.extraction_status == "empty" for page in pages)

    console.print(f"Processed documents: {processed_count}")
    console.print(f"Failed documents: {failed_count}")
    console.print(f"Extracted pages: {len(pages)}")
    console.print(f"Empty pages: {empty_page_count}")
    console.print(f"Pages output: {pages_output}")
    console.print(f"Extraction receipts: {extraction_output}")


@app.command(name="ntrs-build-chunks")
def ntrs_build_chunks(
    pages_input: Annotated[
        Path,
        typer.Option(
            "--pages-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/processed/ntrs/v0_1/pages.jsonl"),
    chunking_config: Annotated[
        Path,
        typer.Option(
            "--chunking-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/chunking_v0_1.yaml"),
    chunks_output: Annotated[
        Path,
        typer.Option(
            "--chunks-output",
            dir_okay=False,
        ),
    ] = Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    receipts_output: Annotated[
        Path,
        typer.Option(
            "--receipts-output",
            dir_okay=False,
        ),
    ] = Path("data/manifests/ntrs_v0_1_chunking.jsonl"),
) -> None:
    """Create citation-preserving overlapping chunks."""

    pages = load_page_records(pages_input)
    config = load_chunking_config(chunking_config)

    chunks, receipts = build_chunks(
        pages=pages,
        config=config,
    )

    write_chunk_records(
        path=chunks_output,
        chunks=chunks,
    )
    write_chunking_receipts(
        path=receipts_output,
        receipts=receipts,
    )

    console.print(f"Loaded pages: {len(pages)}")
    console.print(f"Generated chunks: {len(chunks)}")
    console.print(f"Documents: {len(receipts)}")
    console.print(f"Chunk size: {config.chunk_words} words")
    console.print(f"Overlap: {config.overlap_words} words")
    console.print(f"Chunks output: {chunks_output}")
    console.print(f"Receipts output: {receipts_output}")


@app.command(name="ntrs-bm25-search")
def ntrs_bm25_search(
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Lexical search query.",
        ),
    ],
    chunks_input: Annotated[
        Path,
        typer.Option(
            "--chunks-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    bm25_config: Annotated[
        Path,
        typer.Option(
            "--bm25-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/bm25_v0_1.yaml"),
    top_k: Annotated[
        int | None,
        typer.Option(
            "--top-k",
            min=1,
            max=100,
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            dir_okay=False,
        ),
    ] = None,
) -> None:
    """Search citation-preserving chunks using BM25."""

    config = load_bm25_config(bm25_config)
    chunks = load_chunk_records(chunks_input)

    index = BM25Index(
        chunks=chunks,
        config=config,
    )

    result_limit = top_k if top_k is not None else config.default_top_k

    hits = index.search(
        query=query,
        top_k=result_limit,
    )

    if output is not None:
        write_search_results(
            path=output,
            hits=hits,
        )
        console.print(f"Saved {len(hits)} results to {output}")
        return

    table = Table(title=f"BM25 results: {query}")
    table.add_column("Rank")
    table.add_column("Score")
    table.add_column("Chunk")
    table.add_column("Pages")
    table.add_column("Text")

    for hit in hits:
        chunk = hit.chunk

        preview = chunk.text.replace("\n", " ")[:180]

        table.add_row(
            str(hit.rank),
            f"{hit.score:.4f}",
            chunk.chunk_id,
            (f"{chunk.page_start}-{chunk.page_end}"),
            preview,
        )

    console.print(f"Indexed chunks: {index.document_count}")
    console.print(table)


@app.command(name="ntrs-build-evaluation-candidates")
def ntrs_build_evaluation_candidates(
    queries_input: Annotated[
        Path,
        typer.Option(
            "--queries-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/evaluation/queries_v0_1.jsonl"),
    chunks_input: Annotated[
        Path,
        typer.Option(
            "--chunks-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    bm25_config: Annotated[
        Path,
        typer.Option(
            "--bm25-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/bm25_v0_1.yaml"),
    top_k: Annotated[
        int,
        typer.Option(
            "--top-k",
            min=1,
            max=100,
        ),
    ] = 20,
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            dir_okay=False,
        ),
    ] = Path("data/evaluation/candidates_v0_1.jsonl"),
) -> None:
    """Generate BM25 candidates for annotation."""

    queries = load_evaluation_queries(queries_input)
    chunks = load_chunk_records(chunks_input)
    config = load_bm25_config(bm25_config)

    index = BM25Index(
        chunks=chunks,
        config=config,
    )

    candidates = build_bm25_candidates(
        index=index,
        queries=queries,
        top_k=top_k,
    )

    write_candidate_records(
        path=output,
        records=candidates,
    )

    console.print(f"Queries: {len(queries)}")
    console.print(f"Candidates per query: {top_k}")
    console.print(f"Output: {output}")


@app.command(name="ntrs-evaluate-bm25")
def ntrs_evaluate_bm25(
    queries_input: Annotated[
        Path,
        typer.Option(
            "--queries-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/evaluation/queries_v0_1.jsonl"),
    qrels_input: Annotated[
        Path,
        typer.Option(
            "--qrels-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/evaluation/qrels_v0_1.jsonl"),
    chunks_input: Annotated[
        Path,
        typer.Option(
            "--chunks-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    bm25_config: Annotated[
        Path,
        typer.Option(
            "--bm25-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/bm25_v0_1.yaml"),
    top_k: Annotated[
        int,
        typer.Option(
            "--top-k",
            min=10,
            max=100,
        ),
    ] = 10,
    report_output: Annotated[
        Path,
        typer.Option(
            "--report-output",
            dir_okay=False,
        ),
    ] = Path("artifacts/evaluation/bm25_v0_1.json"),
) -> None:
    """Evaluate the BM25 retrieval baseline."""

    queries = load_evaluation_queries(queries_input)
    judgments = load_relevance_judgments(qrels_input)
    chunks = load_chunk_records(chunks_input)
    config = load_bm25_config(bm25_config)

    index = BM25Index(
        chunks=chunks,
        config=config,
    )

    report = evaluate_bm25(
        index=index,
        queries=queries,
        judgments=judgments,
        top_k=top_k,
    )

    write_evaluation_report(
        path=report_output,
        report=report,
    )

    table = Table(title="BM25 retrieval evaluation")
    table.add_column("Metric")
    table.add_column("Score")

    table.add_row(
        "Recall@5",
        f"{report.recall_at_5:.4f}",
    )
    table.add_row(
        "Recall@10",
        f"{report.recall_at_10:.4f}",
    )
    table.add_row(
        "MRR@10",
        f"{report.mrr_at_10:.4f}",
    )
    table.add_row(
        "NDCG@10",
        f"{report.ndcg_at_10:.4f}",
    )

    console.print(table)
    console.print(f"Report: {report_output}")


if __name__ == "__main__":
    app()
