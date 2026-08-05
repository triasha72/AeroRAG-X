"""Command-line interface for AeroRAG-X."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from aeroragx import __version__
from aeroragx.config import load_config
from aeroragx.ingestion.corpus import (
    build_manifest,
    load_corpus_definition,
    write_manifest,
)
from aeroragx.ingestion.ntrs import NTRSClient, records_to_json_rows

app = typer.Typer(no_args_is_help=True, help="AeroRAG-X development CLI.")
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


if __name__ == "__main__":
    app()
