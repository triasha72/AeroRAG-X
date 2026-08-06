"""Retrieval evaluation and relevance-judgment utilities."""

import json
import math
from collections.abc import Sequence
from pathlib import Path

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from aeroragx.retrieval.bm25 import BM25Index
from aeroragx.retrieval.dense import DenseIndex


class EvaluationQuery(BaseModel):
    """One natural-language retrieval query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)


class RelevanceJudgment(BaseModel):
    """Human relevance labels for one query."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query_id: str = Field(min_length=1)
    relevant_chunk_ids: list[str] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_chunk_ids(
        self,
    ) -> "RelevanceJudgment":
        """Reject duplicated relevance labels."""

        if len(self.relevant_chunk_ids) != len(set(self.relevant_chunk_ids)):
            raise ValueError("relevant_chunk_ids must be unique.")

        return self


class CandidateChunk(BaseModel):
    """One candidate shown during relevance annotation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    rank: int = Field(ge=1)
    score: float = Field(ge=0.0)
    chunk_id: str
    document_id: int
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    text_preview: str
    citation_url: str


class QueryCandidates(BaseModel):
    """Ranked BM25 candidates for one query."""

    model_config = ConfigDict(
        extra="forbid",
    )

    query_id: str
    query: str
    candidates: list[CandidateChunk]


class QueryEvaluation(BaseModel):
    """Retrieval metrics for one query."""

    model_config = ConfigDict(
        extra="forbid",
    )

    query_id: str
    query: str
    relevant_chunk_count: int = Field(ge=1)
    retrieved_chunk_ids: list[str]
    relevant_retrieved_ids: list[str]
    recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_10: float = Field(ge=0.0, le=1.0)
    reciprocal_rank_at_10: float = Field(
        ge=0.0,
        le=1.0,
    )
    ndcg_at_10: float = Field(ge=0.0, le=1.0)


class RetrievalEvaluationReport(BaseModel):
    """Aggregate and per-query retrieval results."""

    model_config = ConfigDict(
        extra="forbid",
    )

    model_name: str
    query_count: int = Field(ge=1)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_10: float = Field(ge=0.0, le=1.0)
    mrr_at_10: float = Field(ge=0.0, le=1.0)
    ndcg_at_10: float = Field(ge=0.0, le=1.0)
    per_query: list[QueryEvaluation]


def load_evaluation_queries(
    path: Path,
) -> list[EvaluationQuery]:
    """Load evaluation queries from JSON Lines."""

    queries: list[EvaluationQuery] = []
    seen_query_ids: set[str] = set()

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            query = EvaluationQuery.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid evaluation query row {line_number}: {exc}") from exc

        if query.query_id in seen_query_ids:
            raise ValueError(f"Duplicate query ID: {query.query_id}")

        seen_query_ids.add(query.query_id)
        queries.append(query)

    if not queries:
        raise ValueError("Evaluation query file contains no queries.")

    return queries


def load_relevance_judgments(
    path: Path,
) -> list[RelevanceJudgment]:
    """Load human relevance judgments from JSON Lines."""

    judgments: list[RelevanceJudgment] = []
    seen_query_ids: set[str] = set()

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped_line = line.strip()

        if not stripped_line:
            continue

        try:
            judgment = RelevanceJudgment.model_validate_json(stripped_line)
        except ValueError as exc:
            raise ValueError(f"Invalid relevance row {line_number}: {exc}") from exc

        if judgment.query_id in seen_query_ids:
            raise ValueError(f"Duplicate relevance judgment: {judgment.query_id}")

        seen_query_ids.add(judgment.query_id)
        judgments.append(judgment)

    if not judgments:
        raise ValueError("Relevance file contains no judgments.")

    return judgments


def recall_at_k(
    retrieved_chunk_ids: Sequence[str],
    relevant_chunk_ids: Sequence[str],
    k: int,
) -> float:
    """Calculate recall among the first k results."""

    if k < 1:
        raise ValueError("k must be at least 1.")

    relevant = set(relevant_chunk_ids)

    if not relevant:
        raise ValueError("At least one relevant chunk is required.")

    retrieved = set(retrieved_chunk_ids[:k])

    return len(retrieved & relevant) / len(relevant)


def reciprocal_rank_at_k(
    retrieved_chunk_ids: Sequence[str],
    relevant_chunk_ids: Sequence[str],
    k: int,
) -> float:
    """Calculate reciprocal rank of the first relevant hit."""

    relevant = set(relevant_chunk_ids)

    for rank, chunk_id in enumerate(
        retrieved_chunk_ids[:k],
        start=1,
    ):
        if chunk_id in relevant:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(
    retrieved_chunk_ids: Sequence[str],
    relevant_chunk_ids: Sequence[str],
    k: int,
) -> float:
    """Calculate binary normalized discounted gain."""

    relevant = set(relevant_chunk_ids)

    if not relevant:
        raise ValueError("At least one relevant chunk is required.")

    discounted_gain = sum(
        1.0 / math.log2(rank + 1)
        for rank, chunk_id in enumerate(
            retrieved_chunk_ids[:k],
            start=1,
        )
        if chunk_id in relevant
    )

    ideal_count = min(
        len(relevant),
        k,
    )

    ideal_gain = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(
            1,
            ideal_count + 1,
        )
    )

    return discounted_gain / ideal_gain


def build_bm25_candidates(
    index: BM25Index,
    queries: Sequence[EvaluationQuery],
    top_k: int = 20,
) -> list[QueryCandidates]:
    """Generate candidate pools for human annotation."""

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    query_candidates: list[QueryCandidates] = []

    for query in queries:
        hits = index.search(
            query=query.query,
            top_k=top_k,
        )

        candidates = [
            CandidateChunk(
                rank=hit.rank,
                score=hit.score,
                chunk_id=hit.chunk.chunk_id,
                document_id=hit.chunk.document_id,
                page_start=hit.chunk.page_start,
                page_end=hit.chunk.page_end,
                text_preview=" ".join(hit.chunk.text.split())[:700],
                citation_url=hit.chunk.citation_url,
            )
            for hit in hits
        ]

        query_candidates.append(
            QueryCandidates(
                query_id=query.query_id,
                query=query.query,
                candidates=candidates,
            )
        )

    return query_candidates


def evaluate_bm25(
    index: BM25Index,
    queries: Sequence[EvaluationQuery],
    judgments: Sequence[RelevanceJudgment],
    top_k: int = 10,
) -> RetrievalEvaluationReport:
    """Evaluate BM25 using human relevance judgments."""

    if top_k < 10:
        raise ValueError("top_k must be at least 10.")

    judgment_by_query = {judgment.query_id: judgment for judgment in judgments}

    query_ids = {query.query_id for query in queries}
    judgment_ids = set(judgment_by_query)

    missing = query_ids - judgment_ids
    unknown = judgment_ids - query_ids

    if missing:
        raise ValueError("Missing relevance judgments for: " + ", ".join(sorted(missing)))

    if unknown:
        raise ValueError("Judgments contain unknown queries: " + ", ".join(sorted(unknown)))

    per_query: list[QueryEvaluation] = []

    for query in queries:
        judgment = judgment_by_query[query.query_id]

        hits = index.search(
            query=query.query,
            top_k=top_k,
        )

        retrieved_chunk_ids = [hit.chunk.chunk_id for hit in hits]

        relevant_set = set(judgment.relevant_chunk_ids)

        relevant_retrieved_ids = [
            chunk_id for chunk_id in retrieved_chunk_ids if chunk_id in relevant_set
        ]

        per_query.append(
            QueryEvaluation(
                query_id=query.query_id,
                query=query.query,
                relevant_chunk_count=len(relevant_set),
                retrieved_chunk_ids=(retrieved_chunk_ids),
                relevant_retrieved_ids=(relevant_retrieved_ids),
                recall_at_5=recall_at_k(
                    retrieved_chunk_ids,
                    judgment.relevant_chunk_ids,
                    5,
                ),
                recall_at_10=recall_at_k(
                    retrieved_chunk_ids,
                    judgment.relevant_chunk_ids,
                    10,
                ),
                reciprocal_rank_at_10=(
                    reciprocal_rank_at_k(
                        retrieved_chunk_ids,
                        judgment.relevant_chunk_ids,
                        10,
                    )
                ),
                ndcg_at_10=ndcg_at_k(
                    retrieved_chunk_ids,
                    judgment.relevant_chunk_ids,
                    10,
                ),
            )
        )

    query_count = len(per_query)

    return RetrievalEvaluationReport(
        model_name="bm25",
        query_count=query_count,
        recall_at_5=round(
            sum(result.recall_at_5 for result in per_query) / query_count,
            6,
        ),
        recall_at_10=round(
            sum(result.recall_at_10 for result in per_query) / query_count,
            6,
        ),
        mrr_at_10=round(
            sum(result.reciprocal_rank_at_10 for result in per_query) / query_count,
            6,
        ),
        ndcg_at_10=round(
            sum(result.ndcg_at_10 for result in per_query) / query_count,
            6,
        ),
        per_query=per_query,
    )


def evaluate_dense(
    index: DenseIndex,
    queries: Sequence[EvaluationQuery],
    judgments: Sequence[RelevanceJudgment],
    top_k: int = 10,
) -> RetrievalEvaluationReport:
    """Evaluate dense retrieval using human judgments."""

    if top_k < 10:
        raise ValueError("top_k must be at least 10.")

    judgment_by_query = {judgment.query_id: judgment for judgment in judgments}

    query_ids = {query.query_id for query in queries}
    judgment_ids = set(judgment_by_query)

    missing = query_ids - judgment_ids
    unknown = judgment_ids - query_ids

    if missing:
        raise ValueError("Missing relevance judgments for: " + ", ".join(sorted(missing)))

    if unknown:
        raise ValueError("Judgments contain unknown queries: " + ", ".join(sorted(unknown)))

    per_query: list[QueryEvaluation] = []

    for query in queries:
        judgment = judgment_by_query[query.query_id]

        hits = index.search(
            query=query.query,
            top_k=top_k,
        )

        retrieved_chunk_ids = [hit.chunk.chunk_id for hit in hits]

        relevant_set = set(judgment.relevant_chunk_ids)

        relevant_retrieved_ids = [
            chunk_id for chunk_id in retrieved_chunk_ids if chunk_id in relevant_set
        ]

        per_query.append(
            QueryEvaluation(
                query_id=query.query_id,
                query=query.query,
                relevant_chunk_count=len(relevant_set),
                retrieved_chunk_ids=(retrieved_chunk_ids),
                relevant_retrieved_ids=(relevant_retrieved_ids),
                recall_at_5=recall_at_k(
                    retrieved_chunk_ids,
                    judgment.relevant_chunk_ids,
                    5,
                ),
                recall_at_10=recall_at_k(
                    retrieved_chunk_ids,
                    judgment.relevant_chunk_ids,
                    10,
                ),
                reciprocal_rank_at_10=(
                    reciprocal_rank_at_k(
                        retrieved_chunk_ids,
                        judgment.relevant_chunk_ids,
                        10,
                    )
                ),
                ndcg_at_10=ndcg_at_k(
                    retrieved_chunk_ids,
                    judgment.relevant_chunk_ids,
                    10,
                ),
            )
        )

    query_count = len(per_query)

    return RetrievalEvaluationReport(
        model_name="dense",
        query_count=query_count,
        recall_at_5=round(
            sum(result.recall_at_5 for result in per_query) / query_count,
            6,
        ),
        recall_at_10=round(
            sum(result.recall_at_10 for result in per_query) / query_count,
            6,
        ),
        mrr_at_10=round(
            sum(result.reciprocal_rank_at_10 for result in per_query) / query_count,
            6,
        ),
        ndcg_at_10=round(
            sum(result.ndcg_at_10 for result in per_query) / query_count,
            6,
        ),
        per_query=per_query,
    )


def write_candidate_records(
    path: Path,
    records: Sequence[QueryCandidates],
) -> None:
    """Write candidate pools as JSON Lines."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = "\n".join(
        json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
        )
        for record in records
    )

    if content:
        content += "\n"

    path.write_text(
        content,
        encoding="utf-8",
    )


def write_evaluation_report(
    path: Path,
    report: RetrievalEvaluationReport,
) -> None:
    """Write an evaluation report as formatted JSON."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
