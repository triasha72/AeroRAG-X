"""Reusable construction of the AeroRAG-X runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from aeroragx.evaluation.retrieval import RetrievalIndex
from aeroragx.generation.adaptive_retrieval import (
    load_adaptive_retrieval_config,
)
from aeroragx.generation.facet_retrieval import (
    FacetAwareEvidenceIndex,
    load_facet_retrieval_config,
)
from aeroragx.generation.grounded import (
    GenerationConfig,
    GroundedAnswerGenerator,
    RerankedEvidenceIndex,
    load_generation_config,
    with_evidence_top_k,
)
from aeroragx.generation.provider_factory import (
    create_configured_generation_provider,
)
from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    load_sufficiency_config,
)
from aeroragx.retrieval.bm25 import (
    BM25Index,
    load_bm25_config,
    load_chunk_records,
)
from aeroragx.retrieval.dense import (
    DenseIndex,
    load_dense_config,
    load_dense_encoder,
    load_dense_index,
)
from aeroragx.retrieval.hybrid import (
    HybridConfig,
    HybridIndex,
    load_hybrid_config,
)
from aeroragx.retrieval.reranker import (
    RerankerConfig,
    RerankerIndex,
    load_cross_encoder_scorer,
    load_reranker_config,
    with_candidate_top_k,
)

type DenseBackendName = Literal[
    "numpy",
    "pgvector",
]


class RuntimeConfigurationError(ValueError):
    """Raised when runtime configurations are incompatible."""


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Paths and settings required to construct AeroRAG-X."""

    chunks_input: Path = Path("data/processed/ntrs/v0_1/chunks.jsonl")

    bm25_config: Path = Path("configs/bm25_v0_1.yaml")

    dense_config: Path = Path("configs/dense_v0_1.yaml")

    hybrid_config: Path = Path("configs/hybrid_v0_1.yaml")

    reranker_config: Path = Path("configs/reranker_v0_1.yaml")

    dense_backend: DenseBackendName = "numpy"

    vector_store_config: Path = Path("configs/vector_store_v0_1.yaml")

    generation_config: Path = Path("configs/generation_v0_1.yaml")

    sufficiency_config: Path = Path("configs/sufficiency_v0_2_1.yaml")

    adaptive_retrieval_config: Path | None = None

    facet_retrieval_config: Path | None = Path("configs/facet_retrieval_v0_1.yaml")

    provider_config: Path | None = None
    http_transport_config: Path | None = None
    provider_runtime_config: Path | None = None

    embeddings_input: Path = Path("artifacts/embeddings/ntrs_v0_1.npy")

    metadata_input: Path = Path("artifacts/embeddings/ntrs_v0_1_metadata.jsonl")

    manifest_input: Path = Path("artifacts/embeddings/ntrs_v0_1_manifest.json")

    candidate_top_k: int | None = None
    evidence_top_k: int | None = None


@dataclass(frozen=True, slots=True)
class AeroRAGRuntime:
    """Fully constructed grounded-generation runtime."""

    generator: GroundedAnswerGenerator
    reranker_settings: RerankerConfig
    generation_settings: GenerationConfig


def load_hybrid_index(
    config: RuntimeConfig,
) -> tuple[HybridIndex, HybridConfig]:
    """Load compatible BM25, dense, and Hybrid RRF indexes."""

    chunks = load_chunk_records(config.chunks_input)

    bm25_settings = load_bm25_config(config.bm25_config)

    dense_settings = load_dense_config(config.dense_config)

    hybrid_settings = load_hybrid_config(config.hybrid_config)

    bm25_index = BM25Index(
        chunks=chunks,
        config=bm25_settings,
    )

    (
        embeddings,
        dense_chunks,
        manifest,
    ) = load_dense_index(
        embeddings_path=config.embeddings_input,
        metadata_path=config.metadata_input,
        manifest_path=config.manifest_input,
    )

    if manifest.model_name != dense_settings.model_name:
        raise RuntimeConfigurationError(
            "Dense configuration model differs from the index manifest."
        )

    corpus_chunk_ids = [chunk.chunk_id for chunk in chunks]

    dense_chunk_ids = [chunk.chunk_id for chunk in dense_chunks]

    if len(corpus_chunk_ids) != len(set(corpus_chunk_ids)):
        raise RuntimeConfigurationError("The BM25 corpus contains duplicate chunk IDs.")

    if len(dense_chunk_ids) != len(set(dense_chunk_ids)):
        raise RuntimeConfigurationError("Dense metadata contains duplicate chunk IDs.")

    if set(corpus_chunk_ids) != set(dense_chunk_ids):
        raise RuntimeConfigurationError(
            "The BM25 corpus and dense metadata contain different chunk IDs."
        )

    encoder = load_dense_encoder(dense_settings)

    dense_index: RetrievalIndex

    if config.dense_backend == "numpy":
        dense_index = DenseIndex(
            embeddings=embeddings,
            chunks=dense_chunks,
            config=dense_settings,
            encoder=encoder,
        )

    elif config.dense_backend == "pgvector":
        try:
            import psycopg

            from aeroragx.retrieval.pgvector_store import (
                PgVectorIndex,
                load_pgvector_config,
                resolve_database_url,
            )

        except ImportError as exc:
            raise RuntimeConfigurationError(
                "The pgvector dense backend requires "
                "the vector dependencies. Install them with "
                '`pip install -e ".[vector]"`.'
            ) from exc

        try:
            vector_settings = load_pgvector_config(config.vector_store_config)

            database_url = resolve_database_url(vector_settings)

            pgvector_index = PgVectorIndex(
                database_url=database_url,
                config=vector_settings,
                dense_config=dense_settings,
                encoder=encoder,
                manifest=manifest,
            )

            database_chunk_count = pgvector_index.document_count

        except (ValueError, psycopg.Error) as exc:
            raise RuntimeConfigurationError(
                f"Could not initialize the pgvector dense backend: {exc}"
            ) from exc

        if database_chunk_count != manifest.chunk_count:
            raise RuntimeConfigurationError(
                "The pgvector database chunk count does not match the dense index manifest."
            )

        dense_index = pgvector_index

    else:
        raise RuntimeConfigurationError(f"Unsupported dense backend: {config.dense_backend!r}.")

    return (
        HybridIndex(
            bm25_index=bm25_index,
            dense_index=dense_index,
            config=hybrid_settings,
        ),
        hybrid_settings,
    )


def load_reranker_index(
    config: RuntimeConfig,
) -> tuple[RerankerIndex, RerankerConfig]:
    """Load Hybrid RRF and cross-encoder reranking."""

    hybrid_index, _ = load_hybrid_index(config)

    reranker_settings = with_candidate_top_k(
        load_reranker_config(config.reranker_config),
        config.candidate_top_k,
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


def load_grounded_runtime(
    config: RuntimeConfig,
) -> AeroRAGRuntime:
    """Construct the complete grounded-generation runtime."""

    (
        reranker_index,
        reranker_settings,
    ) = load_reranker_index(config)

    generation_index: RerankedEvidenceIndex = reranker_index

    if config.facet_retrieval_config is not None:
        generation_index = FacetAwareEvidenceIndex(
            reranker_index,
            load_facet_retrieval_config(config.facet_retrieval_config),
        )

    generation_settings = with_evidence_top_k(
        load_generation_config(config.generation_config),
        config.evidence_top_k,
    )

    if generation_settings.evidence_top_k > reranker_settings.candidate_top_k:
        raise RuntimeConfigurationError(
            "evidence_top_k must not exceed the reranker candidate_top_k."
        )

    try:
        provider = create_configured_generation_provider(
            generation_config=(generation_settings),
            provider_config=(config.provider_config),
            http_transport_config=(config.http_transport_config),
            provider_runtime_config=(config.provider_runtime_config),
        )

    except ValueError as exc:
        raise RuntimeConfigurationError(str(exc)) from exc

    sufficiency_assessor = EvidenceSufficiencyAssessor(
        load_sufficiency_config(config.sufficiency_config)
    )

    adaptive_retrieval_settings = (
        load_adaptive_retrieval_config(config.adaptive_retrieval_config)
        if config.adaptive_retrieval_config is not None
        else None
    )

    generator = GroundedAnswerGenerator(
        index=generation_index,
        provider=provider,
        config=generation_settings,
        sufficiency_assessor=(sufficiency_assessor),
        adaptive_retrieval_config=(adaptive_retrieval_settings),
    )

    return AeroRAGRuntime(
        generator=generator,
        reranker_settings=reranker_settings,
        generation_settings=generation_settings,
    )
