"""Load an existing AeroRAG-X dense index into PostgreSQL + pgvector."""

import argparse
from pathlib import Path

from aeroragx.retrieval.dense import load_dense_index
from aeroragx.retrieval.pgvector_store import (
    load_pgvector_config,
    resolve_database_url,
    upsert_dense_index,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/vector_store_v0_1.yaml"))
    parser.add_argument(
        "--embeddings", type=Path, default=Path("artifacts/embeddings/ntrs_v0_1.npy")
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    )
    return parser.parse_args()


def main() -> None:
    """Load existing persisted embeddings into pgvector."""

    args = parse_args()
    config = load_pgvector_config(args.config)

    database_url = resolve_database_url(config)

    embeddings, chunks, manifest = load_dense_index(
        embeddings_path=args.embeddings,
        metadata_path=args.metadata,
        manifest_path=args.manifest,
    )

    inserted = upsert_dense_index(
        database_url=database_url,
        config=config,
        embeddings=embeddings,
        chunks=chunks,
        manifest=manifest,
    )

    print(f"Loaded {inserted} chunks into PostgreSQL table {config.table_name!r}.")

    print(f"Embedding model: {manifest.model_name}")

    print(f"Embedding dimension: {manifest.embedding_dimension}")

    print(f"Index version: {manifest.version}")


if __name__ == "__main__":
    main()
