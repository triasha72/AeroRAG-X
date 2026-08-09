"""Compare NumPy and PostgreSQL + pgvector dense retrieval."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import numpy as np

from aeroragx.evaluation.retrieval import (
    evaluate_retriever,
    load_evaluation_queries,
    load_relevance_judgments,
)
from aeroragx.retrieval.dense import (
    DenseIndex,
    load_dense_config,
    load_dense_encoder,
    load_dense_index,
)
from aeroragx.retrieval.pgvector_store import (
    PgVectorIndex,
    load_pgvector_config,
    resolve_database_url,
)

TOP_K = 10
WARMUP_QUERY = "aircraft battery thermal management"


def latency_summary(
    values: list[float],
) -> dict[str, float]:
    """Return latency percentiles in milliseconds."""

    array = np.asarray(values, dtype=np.float64)

    return {
        "mean_ms": round(float(np.mean(array)), 3),
        "p50_ms": round(float(np.percentile(array, 50)), 3),
        "p95_ms": round(float(np.percentile(array, 95)), 3),
        "max_ms": round(float(np.max(array)), 3),
    }


def main() -> None:
    """Benchmark NumPy and pgvector retrieval backends."""

    dense_config = load_dense_config(Path("configs/dense_v0_1.yaml"))

    vector_config = load_pgvector_config(Path("configs/vector_store_v0_1.yaml"))

    database_url = resolve_database_url(vector_config)

    embeddings, chunks, manifest = load_dense_index(
        embeddings_path=Path("artifacts/embeddings/ntrs_v0_1.npy"),
        metadata_path=Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl"),
        manifest_path=Path("artifacts/embeddings/ntrs_v0_1_manifest.json"),
    )

    encoder = load_dense_encoder(dense_config)

    numpy_index = DenseIndex(
        embeddings=embeddings,
        chunks=chunks,
        config=dense_config,
        encoder=encoder,
    )

    pgvector_index = PgVectorIndex(
        database_url=database_url,
        config=vector_config,
        dense_config=dense_config,
        encoder=encoder,
        manifest=manifest,
    )

    queries = load_evaluation_queries(Path("data/evaluation/queries_v0_1.jsonl"))

    judgments = load_relevance_judgments(Path("data/evaluation/qrels_v0_2.jsonl"))

    # Warm up the encoder before measuring latency.
    numpy_index.search(
        WARMUP_QUERY,
        top_k=TOP_K,
    )

    pgvector_index.search(
        WARMUP_QUERY,
        top_k=TOP_K,
    )

    numpy_latencies: list[float] = []
    pgvector_latencies: list[float] = []

    comparisons: list[dict[str, object]] = []

    exact_top_10_matches = 0
    overlaps: list[float] = []
    maximum_score_delta = 0.0

    for query in queries:
        numpy_started = perf_counter()

        numpy_hits = numpy_index.search(
            query.query,
            top_k=TOP_K,
        )

        numpy_latencies.append((perf_counter() - numpy_started) * 1000.0)

        pg_started = perf_counter()

        pg_hits = pgvector_index.search(
            query.query,
            top_k=TOP_K,
        )

        pgvector_latencies.append((perf_counter() - pg_started) * 1000.0)

        numpy_ids = [hit.chunk.chunk_id for hit in numpy_hits]

        pg_ids = [hit.chunk.chunk_id for hit in pg_hits]

        exact_match = numpy_ids == pg_ids

        if exact_match:
            exact_top_10_matches += 1

        overlap = len(set(numpy_ids) & set(pg_ids)) / TOP_K

        overlaps.append(overlap)

        score_deltas = [
            abs(numpy_hit.score - pg_hit.score)
            for numpy_hit, pg_hit in zip(
                numpy_hits,
                pg_hits,
                strict=True,
            )
        ]

        query_max_delta = max(score_deltas) if score_deltas else 0.0

        maximum_score_delta = max(
            maximum_score_delta,
            query_max_delta,
        )

        comparisons.append(
            {
                "query_id": query.query_id,
                "query": query.query,
                "exact_top_10_match": exact_match,
                "overlap_at_10": round(
                    overlap,
                    4,
                ),
                "max_score_delta": round(
                    query_max_delta,
                    10,
                ),
                "numpy_chunk_ids": numpy_ids,
                "pgvector_chunk_ids": pg_ids,
            }
        )

    numpy_report = evaluate_retriever(
        index=numpy_index,
        model_name="dense_numpy",
        queries=queries,
        judgments=judgments,
        top_k=TOP_K,
    )

    pgvector_report = evaluate_retriever(
        index=pgvector_index,
        model_name="dense_pgvector",
        queries=queries,
        judgments=judgments,
        top_k=TOP_K,
    )

    result = {
        "benchmark_version": "0.1",
        "query_count": len(queries),
        "corpus_chunk_count": len(chunks),
        "embedding_model": manifest.model_name,
        "embedding_dimension": (manifest.embedding_dimension),
        "top_k": TOP_K,
        "equivalence": {
            "exact_top_10_matches": (exact_top_10_matches),
            "exact_match_rate": round(
                exact_top_10_matches / len(queries),
                4,
            ),
            "mean_overlap_at_10": round(
                float(np.mean(overlaps)),
                4,
            ),
            "maximum_score_delta": round(
                maximum_score_delta,
                10,
            ),
        },
        "numpy": {
            "recall_at_10": (numpy_report.recall_at_10),
            "mrr_at_10": (numpy_report.mrr_at_10),
            "ndcg_at_10": (numpy_report.ndcg_at_10),
            "latency": latency_summary(numpy_latencies),
        },
        "pgvector": {
            "recall_at_10": (pgvector_report.recall_at_10),
            "mrr_at_10": (pgvector_report.mrr_at_10),
            "ndcg_at_10": (pgvector_report.ndcg_at_10),
            "latency": latency_summary(pgvector_latencies),
        },
        "per_query": comparisons,
    }

    output_path = Path("artifacts/evaluation/vector_backend_comparison_v0_1.json")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    print()
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
