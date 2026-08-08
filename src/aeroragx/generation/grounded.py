"""Citation-verified grounded answer generation over reranked evidence."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Protocol, Self, runtime_checkable

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from aeroragx.generation.facet_retrieval import (
    FacetRetrievalTimings,
)
from aeroragx.generation.provider import (
    GenerationProvider,
    ProviderEvidence,
    ProviderResponse,
)
from aeroragx.generation.structured_provider import (
    ProviderTelemetry,
    StructuredGenerationProvider,
)
from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    EvidenceSufficiencyResult,
)
from aeroragx.retrieval.hybrid import RetrieverName
from aeroragx.retrieval.reranker import (
    RerankedSearchHit,
    RerankerSearchTimings,
)

INSUFFICIENT_EVIDENCE_ANSWER = (
    "The retrieved evidence is insufficient to answer this question reliably."
)


class GenerationConfig(BaseModel):
    """Configuration for grounded answer construction and validation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = "0.1"
    provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    evidence_top_k: int = Field(default=5, ge=1, le=100)
    minimum_evidence_count: int = Field(default=1, ge=1, le=100)
    max_context_characters: int = Field(default=12_000, ge=1)
    max_chunk_characters: int = Field(default=3_000, ge=1)
    max_claims: int = Field(default=6, ge=1, le=100)
    require_citations: bool = True
    allow_insufficient_evidence: bool = True
    include_retrieval_metadata: bool = True

    @model_validator(mode="after")
    def validate_generation_limits(self) -> Self:
        """Ensure evidence and context limits are internally consistent."""

        if self.minimum_evidence_count > self.evidence_top_k:
            raise ValueError("minimum_evidence_count must not exceed evidence_top_k.")

        if self.max_chunk_characters > self.max_context_characters:
            raise ValueError("max_chunk_characters must not exceed max_context_characters.")

        return self


class GenerationEvidence(BaseModel):
    """Authoritative reranked evidence available to the generator."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    document_id: int
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    text: str = Field(min_length=1)
    citation_url: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    document_sha256: str = Field(min_length=1)
    reranker_rank: int = Field(ge=1)
    reranker_score: float
    hybrid_rank: int = Field(ge=1)
    hybrid_score: float = Field(gt=0.0)
    retrieved_by: list[RetrieverName] = Field(min_length=1)
    bm25_rank: int | None = Field(default=None, ge=1)
    bm25_score: float | None = Field(default=None, ge=0.0)
    dense_rank: int | None = Field(default=None, ge=1)
    dense_score: float | None = Field(default=None, ge=-1.0, le=1.0)

    @model_validator(mode="after")
    def validate_provenance(self) -> Self:
        """Reject invalid ranges, scores, and source metadata."""

        if self.page_end < self.page_start:
            raise ValueError("page_end must not be smaller than page_start.")

        for name, value in (
            ("reranker_score", self.reranker_score),
            ("hybrid_score", self.hybrid_score),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")

        if len(self.retrieved_by) != len(set(self.retrieved_by)):
            raise ValueError("retrieved_by must not contain duplicates.")

        bm25_present = self.bm25_rank is not None or self.bm25_score is not None
        dense_present = self.dense_rank is not None or self.dense_score is not None

        if (self.bm25_rank is None) != (self.bm25_score is None):
            raise ValueError(
                "bm25_rank and bm25_score must either both be present or both be absent."
            )

        if (self.dense_rank is None) != (self.dense_score is None):
            raise ValueError(
                "dense_rank and dense_score must either both be present or both be absent."
            )

        sources = set(self.retrieved_by)

        if ("bm25" in sources) != bm25_present:
            raise ValueError("BM25 provenance does not match retrieved_by.")

        if ("dense" in sources) != dense_present:
            raise ValueError("Dense provenance does not match retrieved_by.")

        return self


class AnswerCitation(BaseModel):
    """One authoritative citation resolved from a provider evidence ID."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    document_id: int
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    citation_url: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    document_sha256: str = Field(min_length=1)
    reranker_rank: int = Field(ge=1)


class GroundedClaim(BaseModel):
    """One answer claim linked to authoritative citation IDs."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    citation_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_citation_ids(self) -> Self:
        """Reject blank or duplicate citation IDs."""

        if any(not citation_id.strip() for citation_id in self.citation_ids):
            raise ValueError("citation_ids must not contain blank values.")

        if len(self.citation_ids) != len(set(self.citation_ids)):
            raise ValueError("citation_ids must not contain duplicates.")

        return self


class SourceDocument(BaseModel):
    """Deduplicated source-document summary derived from citations."""

    model_config = ConfigDict(extra="forbid")

    document_id: int
    citation_url: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    page_ranges: list[str] = Field(min_length=1)
    chunk_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lists(self) -> Self:
        """Reject duplicate page ranges and chunk IDs."""

        if len(self.page_ranges) != len(set(self.page_ranges)):
            raise ValueError("page_ranges must not contain duplicates.")

        if len(self.chunk_ids) != len(set(self.chunk_ids)):
            raise ValueError("chunk_ids must not contain duplicates.")

        return self


class RetrievalMetadata(BaseModel):
    """Summary of the retrieval and generation settings used."""

    model_config = ConfigDict(extra="forbid")

    retriever: str = Field(min_length=1)
    requested_evidence_top_k: int = Field(ge=1)
    returned_evidence_count: int = Field(ge=0)
    used_evidence_count: int = Field(ge=0)
    reranker_model: str | None = None
    generation_provider: str = Field(min_length=1)
    generation_model: str = Field(min_length=1)
    evidence_sufficiency: EvidenceSufficiencyResult | None = None
    provider_telemetry: ProviderTelemetry | None = None


class RAGStageTimings(BaseModel):
    """Internal wall-clock timings for one grounded-generation request."""

    model_config = ConfigDict(extra="forbid")

    retrieval_ms: float = Field(ge=0.0)
    bm25_ms: float | None = Field(default=None, ge=0.0)
    dense_ms: float | None = Field(default=None, ge=0.0)
    hybrid_fusion_ms: float | None = Field(default=None, ge=0.0)
    reranker_scoring_ms: float | None = Field(default=None, ge=0.0)
    retrieval_search_count: int | None = Field(default=None, ge=1)
    facet_search_count: int | None = Field(default=None, ge=0)
    facet_overhead_ms: float | None = Field(default=None, ge=0.0)
    facet_used: bool | None = None
    evidence_build_ms: float = Field(ge=0.0)
    sufficiency_ms: float | None = Field(default=None, ge=0.0)
    provider_stage_ms: float | None = Field(default=None, ge=0.0)
    citation_resolution_ms: float | None = Field(default=None, ge=0.0)
    total_ms: float = Field(ge=0.0)


class GroundedAnswer(BaseModel):
    """Final grounded answer with claim-level citations."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    claims: list[GroundedClaim] = Field(default_factory=list)
    citations: list[AnswerCitation] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    insufficient_evidence: bool
    retrieval_metadata: RetrievalMetadata | None = None

    _stage_timings: RAGStageTimings | None = PrivateAttr(default=None)

    @property
    def stage_timings(self) -> RAGStageTimings | None:
        """Return a defensive copy of internal stage timings."""

        if self._stage_timings is None:
            return None

        return self._stage_timings.model_copy(deep=True)

    def attach_stage_timings(
        self,
        timings: RAGStageTimings,
    ) -> None:
        """Attach internal timings without changing the public response schema."""

        self._stage_timings = timings.model_copy(deep=True)

    @model_validator(mode="after")
    def validate_answer_state(self) -> Self:
        """Ensure refusal and supported-answer states remain distinct."""

        if self.insufficient_evidence:
            if self.claims or self.citations or self.source_documents:
                raise ValueError(
                    "An insufficient-evidence answer must not contain claims or citations."
                )
        elif not self.claims:
            raise ValueError("A supported answer must contain at least one claim.")

        citation_ids = [citation.citation_id for citation in self.citations]

        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("citations must have unique citation_id values.")

        valid_citations = set(citation_ids)

        for claim in self.claims:
            unknown = set(claim.citation_ids) - valid_citations

            if unknown:
                raise ValueError(
                    "A claim references an unknown citation ID: " + ", ".join(sorted(unknown))
                )

        return self


class RerankedEvidenceIndex(Protocol):
    """Search interface required by grounded answer generation."""

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> Sequence[RerankedSearchHit]:
        """Return reranked evidence candidates."""

        ...


@runtime_checkable
class _FacetTimingIndex(Protocol):
    """Optional facet timing interface used by production retrieval."""

    @property
    def last_timings(self) -> FacetRetrievalTimings | None:
        """Return the latest aggregated facet retrieval timing."""

        ...


@runtime_checkable
class _RerankerTimingIndex(Protocol):
    """Optional reranker timing interface used without facet retrieval."""

    @property
    def last_search_timings(self) -> RerankerSearchTimings | None:
        """Return the latest reranker timing snapshot."""

        ...


class _DetailedRetrievalTimings(BaseModel):
    """Normalized retrieval detail attached to one RAG request."""

    model_config = ConfigDict(extra="forbid")

    bm25_ms: float | None = Field(default=None, ge=0.0)
    dense_ms: float | None = Field(default=None, ge=0.0)
    hybrid_fusion_ms: float | None = Field(default=None, ge=0.0)
    reranker_scoring_ms: float | None = Field(default=None, ge=0.0)
    retrieval_search_count: int | None = Field(default=None, ge=1)
    facet_search_count: int | None = Field(default=None, ge=0)
    facet_overhead_ms: float | None = Field(default=None, ge=0.0)
    facet_used: bool | None = None


def _detailed_retrieval_timings(
    index: RerankedEvidenceIndex,
) -> _DetailedRetrievalTimings:
    """Normalize optional retrieval-component timings after one search."""

    if isinstance(index, _FacetTimingIndex):
        facet_timings = index.last_timings

        if facet_timings is not None:
            return _DetailedRetrievalTimings(
                bm25_ms=facet_timings.bm25_ms,
                dense_ms=facet_timings.dense_ms,
                hybrid_fusion_ms=facet_timings.hybrid_fusion_ms,
                reranker_scoring_ms=(facet_timings.reranker_scoring_ms),
                retrieval_search_count=facet_timings.search_count,
                facet_search_count=facet_timings.facet_search_count,
                facet_overhead_ms=facet_timings.facet_overhead_ms,
                facet_used=facet_timings.used_facets,
            )

    if isinstance(index, _RerankerTimingIndex):
        reranker_timings = index.last_search_timings

        if reranker_timings is not None:
            hybrid_timings = reranker_timings.hybrid

            return _DetailedRetrievalTimings(
                bm25_ms=(hybrid_timings.bm25_ms if hybrid_timings is not None else None),
                dense_ms=(hybrid_timings.dense_ms if hybrid_timings is not None else None),
                hybrid_fusion_ms=(hybrid_timings.fusion_ms if hybrid_timings is not None else None),
                reranker_scoring_ms=(reranker_timings.reranker_scoring_ms),
                retrieval_search_count=1,
                facet_search_count=0,
                facet_overhead_ms=0.0,
                facet_used=False,
            )

    return _DetailedRetrievalTimings()


def load_generation_config(path: Path) -> GenerationConfig:
    """Load and validate a YAML generation configuration."""

    raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(raw_data, dict):
        raise ValueError("Generation configuration must contain a YAML mapping.")

    return GenerationConfig.model_validate(raw_data)


def with_evidence_top_k(
    config: GenerationConfig,
    evidence_top_k: int | None,
) -> GenerationConfig:
    """Return a validated config with an optional evidence-depth override."""

    if evidence_top_k is None:
        return config

    values = config.model_dump(mode="python")
    values["evidence_top_k"] = evidence_top_k

    return GenerationConfig.model_validate(values)


def _build_evidence_record(
    hit: RerankedSearchHit,
    *,
    evidence_id: str,
    text: str,
) -> GenerationEvidence:
    """Convert one reranked hit into authoritative generation evidence."""

    chunk = hit.chunk

    return GenerationEvidence(
        evidence_id=evidence_id,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=text,
        citation_url=chunk.citation_url,
        source_url=chunk.source_url,
        document_sha256=chunk.document_sha256,
        reranker_rank=hit.rank,
        reranker_score=hit.score,
        hybrid_rank=hit.hybrid_rank,
        hybrid_score=hit.hybrid_score,
        retrieved_by=hit.retrieved_by,
        bm25_rank=hit.bm25_rank,
        bm25_score=hit.bm25_score,
        dense_rank=hit.dense_rank,
        dense_score=hit.dense_score,
    )


def build_generation_evidence(
    hits: Sequence[RerankedSearchHit],
    config: GenerationConfig,
) -> list[GenerationEvidence]:
    """Build bounded, deterministic evidence records from reranked hits."""

    selected_hits = list(hits[: config.evidence_top_k])
    chunk_ids = [hit.chunk.chunk_id for hit in selected_hits]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("Reranked evidence contains duplicate chunk IDs.")

    evidence: list[GenerationEvidence] = []
    used_characters = 0

    for hit in selected_hits:
        remaining_characters = config.max_context_characters - used_characters

        if remaining_characters <= 0:
            break

        allowed_characters = min(
            config.max_chunk_characters,
            remaining_characters,
        )
        text = hit.chunk.text[:allowed_characters].strip()

        if not text:
            continue

        evidence_id = f"E{len(evidence) + 1}"
        evidence.append(
            _build_evidence_record(
                hit,
                evidence_id=evidence_id,
                text=text,
            )
        )
        used_characters += len(text)

    return evidence


def _retrieval_metadata(
    *,
    config: GenerationConfig,
    returned_evidence_count: int,
    used_evidence_count: int,
    reranker_model: str | None,
    evidence_sufficiency: EvidenceSufficiencyResult | None,
    provider_telemetry: ProviderTelemetry | None = None,
) -> RetrievalMetadata | None:
    """Build optional retrieval and generation metadata."""

    if not config.include_retrieval_metadata:
        return None

    return RetrievalMetadata(
        retriever="cross_encoder_reranker",
        requested_evidence_top_k=config.evidence_top_k,
        returned_evidence_count=returned_evidence_count,
        used_evidence_count=used_evidence_count,
        reranker_model=reranker_model,
        generation_provider=config.provider,
        generation_model=config.model_name,
        evidence_sufficiency=evidence_sufficiency,
        provider_telemetry=provider_telemetry,
    )


def _insufficient_answer(
    *,
    query: str,
    answer: str,
    config: GenerationConfig,
    returned_evidence_count: int,
    used_evidence_count: int,
    reranker_model: str | None,
    evidence_sufficiency: EvidenceSufficiencyResult | None,
    provider_telemetry: ProviderTelemetry | None = None,
) -> GroundedAnswer:
    """Build a validated insufficient-evidence response."""

    return GroundedAnswer(
        query=query,
        answer=answer,
        claims=[],
        citations=[],
        source_documents=[],
        insufficient_evidence=True,
        retrieval_metadata=_retrieval_metadata(
            config=config,
            returned_evidence_count=returned_evidence_count,
            used_evidence_count=used_evidence_count,
            reranker_model=reranker_model,
            evidence_sufficiency=evidence_sufficiency,
            provider_telemetry=provider_telemetry,
        ),
    )


@dataclass(slots=True)
class _SourceAccumulator:
    """Mutable state while citations are grouped by document."""

    citation_url: str
    source_url: str
    page_ranges: list[str] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)


def _build_source_documents(
    citations: Sequence[AnswerCitation],
) -> list[SourceDocument]:
    """Group citation records into deterministic document summaries."""

    documents: dict[int, _SourceAccumulator] = {}
    document_order: list[int] = []

    for citation in citations:
        document = documents.get(citation.document_id)

        if document is None:
            document = _SourceAccumulator(
                citation_url=citation.citation_url,
                source_url=citation.source_url,
            )
            documents[citation.document_id] = document
            document_order.append(citation.document_id)
        elif (
            document.citation_url != citation.citation_url
            or document.source_url != citation.source_url
        ):
            raise ValueError("Citations contain inconsistent URLs for one document ID.")

        page_range = (
            str(citation.page_start)
            if citation.page_start == citation.page_end
            else f"{citation.page_start}-{citation.page_end}"
        )

        if page_range not in document.page_ranges:
            document.page_ranges.append(page_range)

        if citation.chunk_id not in document.chunk_ids:
            document.chunk_ids.append(citation.chunk_id)

    return [
        SourceDocument(
            document_id=document_id,
            citation_url=documents[document_id].citation_url,
            source_url=documents[document_id].source_url,
            page_ranges=documents[document_id].page_ranges,
            chunk_ids=documents[document_id].chunk_ids,
        )
        for document_id in document_order
    ]


class GroundedAnswerGenerator:
    """Generate answers whose citations are resolved from retrieved evidence."""

    def __init__(
        self,
        index: RerankedEvidenceIndex,
        provider: GenerationProvider,
        config: GenerationConfig,
        sufficiency_assessor: EvidenceSufficiencyAssessor | None = None,
    ) -> None:
        self._index = index
        self._provider = provider
        self._config = config
        self._sufficiency_assessor = sufficiency_assessor

    @property
    def config(self) -> GenerationConfig:
        """Return the validated generation configuration."""

        return self._config

    def generate(
        self,
        query: str,
        *,
        reranker_model: str | None = None,
    ) -> GroundedAnswer:
        """Retrieve, assess, generate, resolve citations, and record timings."""

        total_started_at = perf_counter()
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("query must not be blank.")

        sufficiency_ms: float | None = None
        provider_stage_ms: float | None = None
        citation_resolution_ms: float | None = None

        retrieval_started_at = perf_counter()
        hits = list(
            self._index.search(
                query=normalized_query,
                top_k=self._config.evidence_top_k,
            )
        )
        retrieval_ms = round(
            (perf_counter() - retrieval_started_at) * 1000.0,
            3,
        )
        detailed_retrieval = _detailed_retrieval_timings(
            self._index,
        )

        evidence_started_at = perf_counter()
        evidence = build_generation_evidence(hits, self._config)
        evidence_build_ms = round(
            (perf_counter() - evidence_started_at) * 1000.0,
            3,
        )

        def finalize(answer: GroundedAnswer) -> GroundedAnswer:
            answer.attach_stage_timings(
                RAGStageTimings(
                    retrieval_ms=retrieval_ms,
                    bm25_ms=detailed_retrieval.bm25_ms,
                    dense_ms=detailed_retrieval.dense_ms,
                    hybrid_fusion_ms=(detailed_retrieval.hybrid_fusion_ms),
                    reranker_scoring_ms=(detailed_retrieval.reranker_scoring_ms),
                    retrieval_search_count=(detailed_retrieval.retrieval_search_count),
                    facet_search_count=(detailed_retrieval.facet_search_count),
                    facet_overhead_ms=(detailed_retrieval.facet_overhead_ms),
                    facet_used=detailed_retrieval.facet_used,
                    evidence_build_ms=evidence_build_ms,
                    sufficiency_ms=sufficiency_ms,
                    provider_stage_ms=provider_stage_ms,
                    citation_resolution_ms=citation_resolution_ms,
                    total_ms=round(
                        (perf_counter() - total_started_at) * 1000.0,
                        3,
                    ),
                )
            )
            return answer

        if len(evidence) < self._config.minimum_evidence_count:
            if not self._config.allow_insufficient_evidence:
                raise ValueError(
                    "Retrieved evidence is below minimum_evidence_count and "
                    "insufficient-evidence responses are disabled."
                )

            return finalize(
                _insufficient_answer(
                    query=normalized_query,
                    answer=INSUFFICIENT_EVIDENCE_ANSWER,
                    config=self._config,
                    returned_evidence_count=len(hits),
                    used_evidence_count=len(evidence),
                    reranker_model=reranker_model,
                    evidence_sufficiency=None,
                )
            )

        evidence_sufficiency = None

        if self._sufficiency_assessor is not None:
            sufficiency_started_at = perf_counter()
            evidence_sufficiency = self._sufficiency_assessor.assess(
                query=normalized_query,
                evidence=evidence,
            )
            sufficiency_ms = round(
                (perf_counter() - sufficiency_started_at) * 1000.0,
                3,
            )

            if not evidence_sufficiency.sufficient:
                if not self._config.allow_insufficient_evidence:
                    raise ValueError(
                        "Evidence sufficiency assessment failed and "
                        "insufficient-evidence responses are disabled."
                    )

                return finalize(
                    _insufficient_answer(
                        query=normalized_query,
                        answer=INSUFFICIENT_EVIDENCE_ANSWER,
                        config=self._config,
                        returned_evidence_count=len(hits),
                        used_evidence_count=len(evidence),
                        reranker_model=reranker_model,
                        evidence_sufficiency=evidence_sufficiency,
                    )
                )

        provider_evidence = [
            ProviderEvidence(
                evidence_id=item.evidence_id,
                text=item.text,
            )
            for item in evidence
        ]

        provider_started_at = perf_counter()
        response = self._provider.generate(
            query=normalized_query,
            evidence=provider_evidence,
            max_claims=self._config.max_claims,
        )
        provider_stage_ms = round(
            (perf_counter() - provider_started_at) * 1000.0,
            3,
        )

        provider_telemetry = (
            self._provider.last_telemetry
            if isinstance(
                self._provider,
                StructuredGenerationProvider,
            )
            else None
        )

        resolution_started_at = perf_counter()
        answer = self._resolve_response(
            query=normalized_query,
            response=response,
            evidence=evidence,
            returned_evidence_count=len(hits),
            reranker_model=reranker_model,
            evidence_sufficiency=evidence_sufficiency,
            provider_telemetry=provider_telemetry,
        )
        citation_resolution_ms = round(
            (perf_counter() - resolution_started_at) * 1000.0,
            3,
        )

        return finalize(answer)

    def _resolve_response(
        self,
        *,
        query: str,
        response: ProviderResponse,
        evidence: Sequence[GenerationEvidence],
        returned_evidence_count: int,
        reranker_model: str | None,
        evidence_sufficiency: EvidenceSufficiencyResult | None,
        provider_telemetry: ProviderTelemetry | None,
    ) -> GroundedAnswer:
        """Resolve provider evidence IDs into authoritative citations."""

        if len(response.claims) > self._config.max_claims:
            raise ValueError("Provider returned more claims than max_claims.")

        if response.insufficient_evidence:
            if not self._config.allow_insufficient_evidence:
                raise ValueError(
                    "Provider declared insufficient evidence but that state is disabled."
                )

            if response.claims:
                raise ValueError(
                    "An insufficient-evidence provider response must not contain claims."
                )

            return _insufficient_answer(
                query=query,
                answer=response.answer,
                config=self._config,
                returned_evidence_count=returned_evidence_count,
                used_evidence_count=len(evidence),
                reranker_model=reranker_model,
                evidence_sufficiency=evidence_sufficiency,
                provider_telemetry=provider_telemetry,
            )

        if not response.claims:
            raise ValueError("A supported provider response must contain at least one claim.")

        evidence_by_id = {item.evidence_id: item for item in evidence}
        citations: list[AnswerCitation] = []
        citation_id_by_evidence: dict[str, str] = {}
        claims: list[GroundedClaim] = []

        for claim_number, provider_claim in enumerate(response.claims, start=1):
            evidence_ids = provider_claim.evidence_ids

            if self._config.require_citations and not evidence_ids:
                raise ValueError("Every technical claim must cite at least one evidence ID.")

            if len(evidence_ids) != len(set(evidence_ids)):
                raise ValueError("A provider claim contains duplicate evidence IDs.")

            claim_citation_ids: list[str] = []

            for evidence_id in evidence_ids:
                authoritative_evidence = evidence_by_id.get(evidence_id)

                if authoritative_evidence is None:
                    raise ValueError(f"Provider referenced unknown evidence ID {evidence_id!r}.")

                citation_id = citation_id_by_evidence.get(evidence_id)

                if citation_id is None:
                    citation_id = f"C{len(citations) + 1}"
                    citation_id_by_evidence[evidence_id] = citation_id
                    citations.append(
                        AnswerCitation(
                            citation_id=citation_id,
                            evidence_id=evidence_id,
                            chunk_id=authoritative_evidence.chunk_id,
                            document_id=authoritative_evidence.document_id,
                            page_start=authoritative_evidence.page_start,
                            page_end=authoritative_evidence.page_end,
                            citation_url=authoritative_evidence.citation_url,
                            source_url=authoritative_evidence.source_url,
                            document_sha256=(authoritative_evidence.document_sha256),
                            reranker_rank=authoritative_evidence.reranker_rank,
                        )
                    )

                claim_citation_ids.append(citation_id)

            claims.append(
                GroundedClaim(
                    claim_id=f"CL{claim_number}",
                    text=provider_claim.text,
                    citation_ids=claim_citation_ids,
                )
            )

        return GroundedAnswer(
            query=query,
            answer=response.answer,
            claims=claims,
            citations=citations,
            source_documents=_build_source_documents(citations),
            insufficient_evidence=False,
            retrieval_metadata=_retrieval_metadata(
                config=self._config,
                returned_evidence_count=returned_evidence_count,
                used_evidence_count=len(evidence),
                reranker_model=reranker_model,
                evidence_sufficiency=evidence_sufficiency,
                provider_telemetry=provider_telemetry,
            ),
        )


def write_grounded_answer(path: Path, answer: GroundedAnswer) -> None:
    """Write a grounded answer as formatted JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        answer.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
