"""Command-line interface for AeroRAG-X."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from aeroragx import __version__
from aeroragx.config import load_config
from aeroragx.evaluation.pooling import (
    build_pooled_candidate_records,
    build_qrels_from_annotations,
    load_annotation_records,
    write_annotation_candidate_records,
    write_internal_candidate_records,
    write_relevance_judgments,
)
from aeroragx.evaluation.retrieval import (
    build_bm25_candidates,
    evaluate_bm25,
    evaluate_dense,
    evaluate_retriever,
    load_evaluation_queries,
    load_relevance_judgments,
    write_candidate_records,
    write_evaluation_report,
)
from aeroragx.generation.evaluation import (
    evaluate_grounded_generation,
    load_generation_evaluation_queries,
    write_generation_evaluation_report,
)
from aeroragx.generation.grounded import (
    GenerationConfig,
    GroundedAnswerGenerator,
    load_generation_config,
    with_evidence_top_k,
    write_grounded_answer,
)
from aeroragx.generation.provider import (
    create_generation_provider,
)
from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    load_sufficiency_config,
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
from aeroragx.retrieval.dense import (
    DenseIndex,
    encode_chunks,
    load_dense_config,
    load_dense_encoder,
    load_dense_index,
    write_dense_index,
    write_dense_search_results,
)
from aeroragx.retrieval.hybrid import (
    HybridConfig,
    HybridIndex,
    load_hybrid_config,
    write_hybrid_search_results,
)
from aeroragx.retrieval.reranker import (
    RerankerConfig,
    RerankerIndex,
    load_cross_encoder_scorer,
    load_reranker_config,
    with_candidate_top_k,
    write_reranked_search_results,
    write_reranker_latency_report,
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


@app.command(name="ntrs-build-dense-index")
def ntrs_build_dense_index(
    chunks_input: Annotated[
        Path,
        typer.Option(
            "--chunks-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/processed/ntrs/v0_1/chunks.jsonl"),
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    embeddings_output: Annotated[
        Path,
        typer.Option(
            "--embeddings-output",
            dir_okay=False,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_output: Annotated[
        Path,
        typer.Option(
            "--metadata-output",
            dir_okay=False,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_output: Annotated[
        Path,
        typer.Option(
            "--manifest-output",
            dir_okay=False,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
) -> None:
    """Build the exact dense retrieval index."""

    config = load_dense_config(dense_config)
    chunks = load_chunk_records(chunks_input)
    encoder = load_dense_encoder(config)

    embeddings = encode_chunks(
        chunks=chunks,
        config=config,
        encoder=encoder,
    )

    manifest = write_dense_index(
        embeddings_path=embeddings_output,
        metadata_path=metadata_output,
        manifest_path=manifest_output,
        embeddings=embeddings,
        chunks=chunks,
        config=config,
    )

    console.print(f"Indexed chunks: {manifest.chunk_count}")
    console.print(f"Embedding dimension: {manifest.embedding_dimension}")
    console.print(f"Model: {manifest.model_name}")
    console.print(f"Embeddings: {embeddings_output}")
    console.print(f"Metadata: {metadata_output}")
    console.print(f"Manifest: {manifest_output}")


@app.command(name="ntrs-dense-search")
def ntrs_dense_search(
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Semantic search query.",
        ),
    ],
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
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
    """Search the NASA corpus using dense vectors."""

    config = load_dense_config(dense_config)

    (
        embeddings,
        chunks,
        manifest,
    ) = load_dense_index(
        embeddings_path=embeddings_input,
        metadata_path=metadata_input,
        manifest_path=manifest_input,
    )

    if manifest.model_name != config.model_name:
        raise typer.BadParameter("Dense configuration model differs from the index manifest.")

    encoder = load_dense_encoder(config)

    index = DenseIndex(
        embeddings=embeddings,
        chunks=chunks,
        config=config,
        encoder=encoder,
    )

    result_limit = top_k if top_k is not None else config.default_top_k

    hits = index.search(
        query=query,
        top_k=result_limit,
    )

    if output is not None:
        write_dense_search_results(
            path=output,
            hits=hits,
        )

        console.print(f"Saved {len(hits)} results to {output}")
        return

    table = Table(title=f"Dense results: {query}")
    table.add_column("Rank")
    table.add_column("Score")
    table.add_column("Chunk")
    table.add_column("Pages")
    table.add_column("Text")

    for hit in hits:
        chunk = hit.chunk

        table.add_row(
            str(hit.rank),
            f"{hit.score:.4f}",
            chunk.chunk_id,
            (f"{chunk.page_start}-{chunk.page_end}"),
            " ".join(chunk.text.split())[:180],
        )

    console.print(f"Indexed chunks: {index.document_count}")
    console.print(table)


@app.command(name="ntrs-evaluate-dense")
def ntrs_evaluate_dense(
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
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
    ] = Path("artifacts/evaluation/dense_v0_1.json"),
) -> None:
    """Evaluate the dense retrieval baseline."""

    queries = load_evaluation_queries(queries_input)
    judgments = load_relevance_judgments(qrels_input)
    config = load_dense_config(dense_config)

    (
        embeddings,
        chunks,
        manifest,
    ) = load_dense_index(
        embeddings_path=embeddings_input,
        metadata_path=metadata_input,
        manifest_path=manifest_input,
    )

    if manifest.model_name != config.model_name:
        raise typer.BadParameter("Dense configuration model differs from the index manifest.")

    encoder = load_dense_encoder(config)

    index = DenseIndex(
        embeddings=embeddings,
        chunks=chunks,
        config=config,
        encoder=encoder,
    )

    report = evaluate_dense(
        index=index,
        queries=queries,
        judgments=judgments,
        top_k=top_k,
    )

    write_evaluation_report(
        path=report_output,
        report=report,
    )

    table = Table(title="Dense retrieval evaluation")
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


@app.command(name="ntrs-build-pooled-candidates")
def ntrs_build_pooled_candidates(
    queries_input: Annotated[
        Path,
        typer.Option(
            "--queries-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/evaluation/queries_v0_1.jsonl"),
    previous_qrels_input: Annotated[
        Path,
        typer.Option(
            "--previous-qrels-input",
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    top_k_per_retriever: Annotated[
        int,
        typer.Option(
            "--top-k-per-retriever",
            min=1,
            max=100,
        ),
    ] = 20,
    shuffle_seed: Annotated[
        int,
        typer.Option("--shuffle-seed"),
    ] = 42,
    internal_output: Annotated[
        Path,
        typer.Option(
            "--internal-output",
            dir_okay=False,
        ),
    ] = Path("data/evaluation/candidates_v0_2_internal.jsonl"),
    annotation_output: Annotated[
        Path,
        typer.Option(
            "--annotation-output",
            dir_okay=False,
        ),
    ] = Path("data/evaluation/candidates_v0_2_annotation.jsonl"),
) -> None:
    """Build blinded BM25 and dense candidate pools."""

    queries = load_evaluation_queries(queries_input)
    previous_judgments = load_relevance_judgments(previous_qrels_input)
    chunks = load_chunk_records(chunks_input)

    bm25_settings = load_bm25_config(bm25_config)
    dense_settings = load_dense_config(dense_config)

    bm25_index = BM25Index(
        chunks=chunks,
        config=bm25_settings,
    )

    (
        embeddings,
        dense_chunks,
        manifest,
    ) = load_dense_index(
        embeddings_path=embeddings_input,
        metadata_path=metadata_input,
        manifest_path=manifest_input,
    )

    if manifest.model_name != dense_settings.model_name:
        raise typer.BadParameter("Dense configuration model differs from the index manifest.")

    corpus_chunk_ids = [chunk.chunk_id for chunk in chunks]
    dense_chunk_ids = [chunk.chunk_id for chunk in dense_chunks]

    if len(corpus_chunk_ids) != len(set(corpus_chunk_ids)):
        raise typer.BadParameter("The corpus contains duplicate chunk IDs.")

    if len(dense_chunk_ids) != len(set(dense_chunk_ids)):
        raise typer.BadParameter("Dense metadata contains duplicate chunk IDs.")

    if set(corpus_chunk_ids) != set(dense_chunk_ids):
        raise typer.BadParameter("The BM25 corpus and dense metadata contain different chunk IDs.")

    encoder = load_dense_encoder(dense_settings)

    dense_index = DenseIndex(
        embeddings=embeddings,
        chunks=dense_chunks,
        config=dense_settings,
        encoder=encoder,
    )

    (
        internal_records,
        annotation_records,
    ) = build_pooled_candidate_records(
        queries=queries,
        previous_judgments=(previous_judgments),
        chunks=chunks,
        bm25_index=bm25_index,
        dense_index=dense_index,
        top_k_per_retriever=(top_k_per_retriever),
        shuffle_seed=shuffle_seed,
    )

    write_internal_candidate_records(
        path=internal_output,
        records=internal_records,
    )
    write_annotation_candidate_records(
        path=annotation_output,
        records=annotation_records,
    )

    table = Table(title="Pooled candidate generation")
    table.add_column("Query")
    table.add_column("Candidates")

    for record in internal_records:
        table.add_row(
            record.query_id,
            str(len(record.candidates)),
        )

    total_candidates = sum(len(record.candidates) for record in internal_records)

    console.print(table)
    console.print(f"Total candidates: {total_candidates}")
    console.print(f"Internal output: {internal_output}")
    console.print(f"Annotation output: {annotation_output}")


@app.command(name="ntrs-build-qrels-from-annotations")
def ntrs_build_qrels_from_annotations(
    annotations_input: Annotated[
        Path,
        typer.Option(
            "--annotations-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/evaluation/candidates_v0_2_annotation.jsonl"),
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            dir_okay=False,
        ),
    ] = Path("data/evaluation/qrels_v0_2.jsonl"),
) -> None:
    """Create qrels from completed annotations."""

    annotation_records = load_annotation_records(annotations_input)

    judgments = build_qrels_from_annotations(annotation_records)

    write_relevance_judgments(
        path=output,
        judgments=judgments,
    )

    relevant_count = sum(len(judgment.relevant_chunk_ids) for judgment in judgments)

    console.print(f"Queries: {len(judgments)}")
    console.print(f"Relevant chunks: {relevant_count}")
    console.print(f"Output: {output}")


def _load_hybrid_index_from_paths(
    chunks_input: Path,
    bm25_config: Path,
    dense_config: Path,
    hybrid_config: Path,
    embeddings_input: Path,
    metadata_input: Path,
    manifest_input: Path,
) -> tuple[HybridIndex, HybridConfig]:
    """Load compatible BM25, dense, and hybrid indexes."""

    chunks = load_chunk_records(chunks_input)
    bm25_settings = load_bm25_config(bm25_config)
    dense_settings = load_dense_config(dense_config)
    hybrid_settings = load_hybrid_config(hybrid_config)

    bm25_index = BM25Index(
        chunks=chunks,
        config=bm25_settings,
    )

    (
        embeddings,
        dense_chunks,
        manifest,
    ) = load_dense_index(
        embeddings_path=embeddings_input,
        metadata_path=metadata_input,
        manifest_path=manifest_input,
    )

    if manifest.model_name != dense_settings.model_name:
        raise typer.BadParameter("Dense configuration model differs from the index manifest.")

    corpus_chunk_ids = [chunk.chunk_id for chunk in chunks]
    dense_chunk_ids = [chunk.chunk_id for chunk in dense_chunks]

    if len(corpus_chunk_ids) != len(set(corpus_chunk_ids)):
        raise typer.BadParameter("The BM25 corpus contains duplicate chunk IDs.")

    if len(dense_chunk_ids) != len(set(dense_chunk_ids)):
        raise typer.BadParameter("Dense metadata contains duplicate chunk IDs.")

    if set(corpus_chunk_ids) != set(dense_chunk_ids):
        raise typer.BadParameter("The BM25 corpus and dense metadata contain different chunk IDs.")

    encoder = load_dense_encoder(dense_settings)

    dense_index = DenseIndex(
        embeddings=embeddings,
        chunks=dense_chunks,
        config=dense_settings,
        encoder=encoder,
    )

    return (
        HybridIndex(
            bm25_index=bm25_index,
            dense_index=dense_index,
            config=hybrid_settings,
        ),
        hybrid_settings,
    )


@app.command(name="ntrs-hybrid-search")
def ntrs_hybrid_search(
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Hybrid lexical and semantic query.",
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    hybrid_config: Annotated[
        Path,
        typer.Option(
            "--hybrid-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/hybrid_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    top_k: Annotated[
        int | None,
        typer.Option("--top-k", min=1, max=100),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", dir_okay=False),
    ] = None,
) -> None:
    """Search using BM25+dense reciprocal-rank fusion."""

    index, hybrid_settings = _load_hybrid_index_from_paths(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
    )

    result_limit = top_k if top_k is not None else hybrid_settings.default_top_k

    hits = index.search(query=query, top_k=result_limit)

    if output is not None:
        write_hybrid_search_results(path=output, hits=hits)
        console.print(f"Saved {len(hits)} results to {output}")
        return

    table = Table(title=f"Hybrid RRF results: {query}")
    table.add_column("Rank")
    table.add_column("RRF score")
    table.add_column("Sources")
    table.add_column("BM25 rank")
    table.add_column("Dense rank")
    table.add_column("Chunk")
    table.add_column("Pages")
    table.add_column("Text")

    for hit in hits:
        chunk = hit.chunk
        table.add_row(
            str(hit.rank),
            f"{hit.score:.6f}",
            "+".join(hit.retrieved_by),
            str(hit.bm25_rank) if hit.bm25_rank is not None else "-",
            str(hit.dense_rank) if hit.dense_rank is not None else "-",
            chunk.chunk_id,
            f"{chunk.page_start}-{chunk.page_end}",
            " ".join(chunk.text.split())[:180],
        )

    console.print(table)


@app.command(name="ntrs-evaluate-hybrid")
def ntrs_evaluate_hybrid(
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
    ] = Path("data/evaluation/qrels_v0_2.jsonl"),
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    hybrid_config: Annotated[
        Path,
        typer.Option(
            "--hybrid-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/hybrid_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    top_k: Annotated[
        int,
        typer.Option("--top-k", min=10, max=100),
    ] = 10,
    report_output: Annotated[
        Path,
        typer.Option("--report-output", dir_okay=False),
    ] = Path("artifacts/evaluation/hybrid_v0_2.json"),
) -> None:
    """Evaluate reciprocal-rank-fusion retrieval."""

    queries = load_evaluation_queries(queries_input)
    judgments = load_relevance_judgments(qrels_input)

    index, _ = _load_hybrid_index_from_paths(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
    )

    report = evaluate_retriever(
        index=index,
        model_name="hybrid_rrf",
        queries=queries,
        judgments=judgments,
        top_k=top_k,
    )

    write_evaluation_report(path=report_output, report=report)

    table = Table(title="Hybrid RRF retrieval evaluation")
    table.add_column("Metric")
    table.add_column("Score")
    table.add_row("Recall@5", f"{report.recall_at_5:.4f}")
    table.add_row("Recall@10", f"{report.recall_at_10:.4f}")
    table.add_row("MRR@10", f"{report.mrr_at_10:.4f}")
    table.add_row("NDCG@10", f"{report.ndcg_at_10:.4f}")

    console.print(table)
    console.print(f"Report: {report_output}")


def _load_reranker_index_from_paths(
    chunks_input: Path,
    bm25_config: Path,
    dense_config: Path,
    hybrid_config: Path,
    reranker_config: Path,
    embeddings_input: Path,
    metadata_input: Path,
    manifest_input: Path,
    candidate_top_k: int | None,
) -> tuple[RerankerIndex, RerankerConfig]:
    """Load the complete Hybrid RRF and cross-encoder stack."""

    hybrid_index, _ = _load_hybrid_index_from_paths(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
    )

    reranker_settings = with_candidate_top_k(
        load_reranker_config(reranker_config),
        candidate_top_k,
    )
    scorer = load_cross_encoder_scorer(reranker_settings)

    return (
        RerankerIndex(
            hybrid_index=hybrid_index,
            scorer=scorer,
            config=reranker_settings,
        ),
        reranker_settings,
    )


@app.command(name="ntrs-reranker-search")
def ntrs_reranker_search(
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help="Query to retrieve and rerank.",
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    hybrid_config: Annotated[
        Path,
        typer.Option(
            "--hybrid-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/hybrid_v0_1.yaml"),
    reranker_config: Annotated[
        Path,
        typer.Option(
            "--reranker-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/reranker_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    candidate_top_k: Annotated[
        int | None,
        typer.Option(
            "--candidate-top-k",
            min=1,
            max=100,
        ),
    ] = None,
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
    """Retrieve with Hybrid RRF and rerank with a cross-encoder."""

    index, settings = _load_reranker_index_from_paths(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        reranker_config=reranker_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
        candidate_top_k=candidate_top_k,
    )

    result_limit = top_k if top_k is not None else settings.default_top_k

    hits = index.search(
        query=query,
        top_k=result_limit,
    )

    if output is not None:
        write_reranked_search_results(
            path=output,
            hits=hits,
        )
        console.print(f"Saved {len(hits)} results to {output}")
        return

    table = Table(title=f"Cross-encoder reranked results: {query}")
    table.add_column("Rank")
    table.add_column("CE score")
    table.add_column("Hybrid rank")
    table.add_column("RRF score")
    table.add_column("Sources")
    table.add_column("BM25 rank")
    table.add_column("Dense rank")
    table.add_column("Chunk")
    table.add_column("Pages")
    table.add_column("Text")

    for hit in hits:
        chunk = hit.chunk
        table.add_row(
            str(hit.rank),
            f"{hit.score:.6f}",
            str(hit.hybrid_rank),
            f"{hit.hybrid_score:.6f}",
            "+".join(hit.retrieved_by),
            (str(hit.bm25_rank) if hit.bm25_rank is not None else "-"),
            (str(hit.dense_rank) if hit.dense_rank is not None else "-"),
            chunk.chunk_id,
            f"{chunk.page_start}-{chunk.page_end}",
            " ".join(chunk.text.split())[:180],
        )

    console.print(table)
    console.print(f"Model: {settings.model_name}")
    console.print(f"Reranked candidates: {index.last_pair_count}")
    console.print(f"Cross-encoder scoring seconds: {index.last_scoring_seconds:.4f}")


@app.command(name="ntrs-evaluate-reranker")
def ntrs_evaluate_reranker(
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
    ] = Path("data/evaluation/qrels_v0_2.jsonl"),
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    hybrid_config: Annotated[
        Path,
        typer.Option(
            "--hybrid-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/hybrid_v0_1.yaml"),
    reranker_config: Annotated[
        Path,
        typer.Option(
            "--reranker-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/reranker_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    candidate_top_k: Annotated[
        int | None,
        typer.Option(
            "--candidate-top-k",
            min=10,
            max=100,
        ),
    ] = None,
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
    ] = Path("artifacts/evaluation/reranker_top20_v0_2.json"),
    latency_output: Annotated[
        Path | None,
        typer.Option(
            "--latency-output",
            dir_okay=False,
        ),
    ] = None,
    hardware_note: Annotated[
        str | None,
        typer.Option("--hardware-note"),
    ] = None,
) -> None:
    """Evaluate cross-encoder reranking on pooled judgments."""

    queries = load_evaluation_queries(queries_input)
    judgments = load_relevance_judgments(qrels_input)

    index, settings = _load_reranker_index_from_paths(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        reranker_config=reranker_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
        candidate_top_k=candidate_top_k,
    )

    index.reset_timing()

    report = evaluate_retriever(
        index=index,
        model_name="cross_encoder_reranker",
        queries=queries,
        judgments=judgments,
        top_k=top_k,
    )

    write_evaluation_report(
        path=report_output,
        report=report,
    )

    latency_report = index.build_latency_report(hardware_note=hardware_note)

    if latency_output is not None:
        write_reranker_latency_report(
            path=latency_output,
            report=latency_report,
        )

    table = Table(title="Cross-encoder reranker evaluation")
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
    console.print(f"Model: {settings.model_name}")
    console.print(f"Candidate depth: {settings.candidate_top_k}")
    console.print(f"Scored pairs: {latency_report.pair_count}")
    console.print(f"Scoring seconds: {latency_report.total_seconds:.4f}")
    console.print(f"Milliseconds per pair: {latency_report.milliseconds_per_pair:.4f}")
    console.print(f"Report: {report_output}")

    if latency_output is not None:
        console.print(f"Latency report: {latency_output}")


def _load_grounded_answer_generator(
    chunks_input: Path,
    bm25_config: Path,
    dense_config: Path,
    hybrid_config: Path,
    reranker_config: Path,
    generation_config: Path,
    sufficiency_config: Path,
    embeddings_input: Path,
    metadata_input: Path,
    manifest_input: Path,
    candidate_top_k: int | None,
    evidence_top_k: int | None,
) -> tuple[
    GroundedAnswerGenerator,
    RerankerConfig,
    GenerationConfig,
]:
    """Load retrieval, reranking, and grounded-generation components."""

    (
        reranker_index,
        reranker_settings,
    ) = _load_reranker_index_from_paths(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        reranker_config=reranker_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
        candidate_top_k=candidate_top_k,
    )

    generation_settings = with_evidence_top_k(
        load_generation_config(generation_config),
        evidence_top_k,
    )

    if generation_settings.evidence_top_k > reranker_settings.candidate_top_k:
        raise typer.BadParameter("evidence_top_k must not exceed the reranker candidate_top_k.")

    try:
        provider = create_generation_provider(generation_settings.provider)
    except ValueError as exc:
        raise typer.BadParameter(
            str(exc),
            param_hint=("--generation-config"),
        ) from exc

    sufficiency_assessor = EvidenceSufficiencyAssessor(load_sufficiency_config(sufficiency_config))

    generator = GroundedAnswerGenerator(
        index=reranker_index,
        provider=provider,
        config=generation_settings,
        sufficiency_assessor=sufficiency_assessor,
    )

    return (
        generator,
        reranker_settings,
        generation_settings,
    )


@app.command(name="ntrs-grounded-answer")
def ntrs_grounded_answer(
    query: Annotated[
        str,
        typer.Option(
            "--query",
            "-q",
            help=("Question answered from reranked NASA evidence."),
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    hybrid_config: Annotated[
        Path,
        typer.Option(
            "--hybrid-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/hybrid_v0_1.yaml"),
    reranker_config: Annotated[
        Path,
        typer.Option(
            "--reranker-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/reranker_v0_1.yaml"),
    generation_config: Annotated[
        Path,
        typer.Option(
            "--generation-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/generation_v0_1.yaml"),
    sufficiency_config: Annotated[
        Path,
        typer.Option(
            "--sufficiency-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/sufficiency_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    candidate_top_k: Annotated[
        int | None,
        typer.Option(
            "--candidate-top-k",
            min=1,
            max=100,
        ),
    ] = None,
    evidence_top_k: Annotated[
        int | None,
        typer.Option(
            "--evidence-top-k",
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
    """Generate a citation-verified answer from reranked evidence."""

    (
        generator,
        reranker_settings,
        generation_settings,
    ) = _load_grounded_answer_generator(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        reranker_config=reranker_config,
        generation_config=generation_config,
        sufficiency_config=sufficiency_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
        candidate_top_k=candidate_top_k,
        evidence_top_k=evidence_top_k,
    )

    answer = generator.generate(
        query,
        reranker_model=(reranker_settings.model_name),
    )

    if output is not None:
        write_grounded_answer(
            output,
            answer,
        )
        console.print(f"Saved grounded answer to {output}")
        return

    console.rule("[bold]Grounded answer[/bold]")
    console.print(answer.answer)
    console.print()
    console.print(f"Insufficient evidence: {answer.insufficient_evidence}")
    console.print(f"Generation provider: {generation_settings.provider}")
    console.print(f"Generation model: {generation_settings.model_name}")
    console.print(f"Reranker model: {reranker_settings.model_name}")

    if answer.claims:
        claims_table = Table(title="Grounded claims")
        claims_table.add_column("Claim")
        claims_table.add_column("Text")
        claims_table.add_column("Citations")

        for claim in answer.claims:
            claims_table.add_row(
                claim.claim_id,
                claim.text,
                ", ".join(claim.citation_ids),
            )

        console.print(claims_table)

    if answer.citations:
        citation_table = Table(title="Authoritative citations")
        citation_table.add_column("Citation")
        citation_table.add_column("Document")
        citation_table.add_column("Pages")
        citation_table.add_column("Chunk")
        citation_table.add_column("Reranker rank")
        citation_table.add_column("NASA citation")

        for citation in answer.citations:
            pages = (
                str(citation.page_start)
                if (citation.page_start == citation.page_end)
                else (f"{citation.page_start}-{citation.page_end}")
            )

            citation_table.add_row(
                citation.citation_id,
                str(citation.document_id),
                pages,
                citation.chunk_id,
                str(citation.reranker_rank),
                citation.citation_url,
            )

        console.print(citation_table)


@app.command(name="ntrs-evaluate-generation")
def ntrs_evaluate_generation(
    queries_input: Annotated[
        Path,
        typer.Option(
            "--queries-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("data/evaluation/generation_queries_v0_1.jsonl"),
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
    dense_config: Annotated[
        Path,
        typer.Option(
            "--dense-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/dense_v0_1.yaml"),
    hybrid_config: Annotated[
        Path,
        typer.Option(
            "--hybrid-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/hybrid_v0_1.yaml"),
    reranker_config: Annotated[
        Path,
        typer.Option(
            "--reranker-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/reranker_v0_1.yaml"),
    generation_config: Annotated[
        Path,
        typer.Option(
            "--generation-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/generation_v0_1.yaml"),
    sufficiency_config: Annotated[
        Path,
        typer.Option(
            "--sufficiency-config",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("configs/sufficiency_v0_1.yaml"),
    embeddings_input: Annotated[
        Path,
        typer.Option(
            "--embeddings-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1.npy"),
    metadata_input: Annotated[
        Path,
        typer.Option(
            "--metadata-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    manifest_input: Annotated[
        Path,
        typer.Option(
            "--manifest-input",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    candidate_top_k: Annotated[
        int | None,
        typer.Option(
            "--candidate-top-k",
            min=1,
            max=100,
        ),
    ] = None,
    evidence_top_k: Annotated[
        int | None,
        typer.Option(
            "--evidence-top-k",
            min=1,
            max=100,
        ),
    ] = None,
    report_output: Annotated[
        Path,
        typer.Option(
            "--report-output",
            dir_okay=False,
        ),
    ] = Path("artifacts/evaluation/generation_v0_2.json"),
) -> None:
    """Evaluate grounded answers on labeled generation queries."""

    queries = load_generation_evaluation_queries(queries_input)

    (
        generator,
        reranker_settings,
        generation_settings,
    ) = _load_grounded_answer_generator(
        chunks_input=chunks_input,
        bm25_config=bm25_config,
        dense_config=dense_config,
        hybrid_config=hybrid_config,
        reranker_config=reranker_config,
        generation_config=generation_config,
        sufficiency_config=sufficiency_config,
        embeddings_input=embeddings_input,
        metadata_input=metadata_input,
        manifest_input=manifest_input,
        candidate_top_k=candidate_top_k,
        evidence_top_k=evidence_top_k,
    )

    report = evaluate_grounded_generation(
        generator=generator,
        queries=queries,
        generation_provider=(generation_settings.provider),
        generation_model=(generation_settings.model_name),
        reranker_model=(reranker_settings.model_name),
    )

    write_generation_evaluation_report(
        report_output,
        report,
    )

    table = Table(title="Grounded-generation evaluation")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row(
        "Queries",
        str(report.query_count),
    )
    table.add_row(
        "Answerability accuracy",
        f"{report.answerability_accuracy:.4f}",
    )
    table.add_row(
        "Answerable completion",
        f"{report.answerable_completion_rate:.4f}",
    )
    table.add_row(
        "Unsupported refusal",
        f"{report.unsupported_refusal_rate:.4f}",
    )
    table.add_row(
        "Claim citation coverage",
        f"{report.claim_citation_coverage_rate:.4f}",
    )
    table.add_row(
        "Citation validity",
        f"{report.citation_reference_validity_rate:.4f}",
    )
    table.add_row(
        "Source coverage",
        f"{report.source_document_coverage_rate:.4f}",
    )
    table.add_row(
        "Expected-term recall",
        f"{report.expected_term_recall:.4f}",
    )
    table.add_row(
        "Structural validity",
        f"{report.structural_validity_rate:.4f}",
    )

    console.print(table)
    console.print(f"Report: {report_output}")


if __name__ == "__main__":
    app()
