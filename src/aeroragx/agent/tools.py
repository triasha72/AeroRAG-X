"""Bounded, typed tool wrappers for the future AeroRAG-X agent graph."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from time import perf_counter

from aeroragx.agent.contracts import (
    CheckEvidenceSufficiencyRequest,
    CheckEvidenceSufficiencyResult,
    CompareSourcesRequest,
    CompareSourcesResult,
    EvidenceReference,
    FetchSourceContextRequest,
    FetchSourceContextResult,
    HybridRetrieveRequest,
    HybridRetrieveResult,
    SourceComparisonRecord,
    SourceContextRecord,
    SufficiencyAssessment,
    ToolCallRecord,
    ValidateCitationsRequest,
    ValidateCitationsResult,
)

HybridRetrieveBackend = Callable[[str, int], Sequence[EvidenceReference]]
SourceContextBackend = Callable[[Sequence[str]], Sequence[SourceContextRecord]]
SufficiencyBackend = Callable[[str, Sequence[str]], SufficiencyAssessment]
SourceComparisonBackend = Callable[[Sequence[str]], Sequence[SourceComparisonRecord]]


def _latency_ms(started_at: float) -> float:
    return max((perf_counter() - started_at) * 1000.0, 0.0)


def _backend_failure(
    *,
    tool_call_id: str,
    tool_name: str,
    started_at: float,
    exc: Exception,
) -> ToolCallRecord:
    """Build bounded structured error metadata without propagating backend exceptions."""

    allowed_names = {
        "hybrid_retrieve",
        "fetch_source_context",
        "check_evidence_sufficiency",
        "compare_sources",
    }
    if tool_name not in allowed_names:
        raise ValueError(f"Unsupported backend tool name: {tool_name}.")

    # The concrete string is validated by ToolCallRecord after construction.
    return ToolCallRecord.model_validate(
        {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "status": "error",
            "latency_ms": _latency_ms(started_at),
            "error": {
                "code": "backend_error",
                "message": f"{type(exc).__name__}: {exc}"[:500],
            },
        }
    )


def hybrid_retrieve(
    request: HybridRetrieveRequest,
    *,
    backend: HybridRetrieveBackend,
    tool_call_id: str,
) -> HybridRetrieveResult:
    """Execute bounded hybrid retrieval through an injected backend."""

    started_at = perf_counter()
    try:
        evidence = [
            EvidenceReference.model_validate(item.model_dump(mode="python"))
            for item in backend(request.query, request.top_k)
        ]
    except Exception as exc:
        return HybridRetrieveResult(
            call=_backend_failure(
                tool_call_id=tool_call_id,
                tool_name="hybrid_retrieve",
                started_at=started_at,
                exc=exc,
            ),
            query=request.query,
            evidence=[],
        )

    return HybridRetrieveResult(
        call=ToolCallRecord(
            tool_call_id=tool_call_id,
            tool_name="hybrid_retrieve",
            status="success",
            latency_ms=_latency_ms(started_at),
        ),
        query=request.query,
        evidence=evidence,
    )


def fetch_source_context(
    request: FetchSourceContextRequest,
    *,
    backend: SourceContextBackend,
    tool_call_id: str,
) -> FetchSourceContextResult:
    """Fetch authoritative context only for requested evidence identifiers."""

    started_at = perf_counter()
    try:
        contexts = [
            SourceContextRecord.model_validate(item.model_dump(mode="python"))
            for item in backend(request.evidence_ids)
        ]
        requested_ids = set(request.evidence_ids)
        returned_ids = {context.evidence_id for context in contexts}
        if not returned_ids.issubset(requested_ids):
            raise ValueError("Source backend returned context for an unrequested evidence ID.")
    except Exception as exc:
        return FetchSourceContextResult(
            call=_backend_failure(
                tool_call_id=tool_call_id,
                tool_name="fetch_source_context",
                started_at=started_at,
                exc=exc,
            ),
            contexts=[],
        )

    return FetchSourceContextResult(
        call=ToolCallRecord(
            tool_call_id=tool_call_id,
            tool_name="fetch_source_context",
            status="success",
            latency_ms=_latency_ms(started_at),
        ),
        contexts=contexts,
    )


def check_evidence_sufficiency(
    request: CheckEvidenceSufficiencyRequest,
    *,
    backend: SufficiencyBackend,
    tool_call_id: str,
) -> CheckEvidenceSufficiencyResult:
    """Execute the existing sufficiency policy through a typed agent-tool boundary."""

    started_at = perf_counter()
    try:
        assessment = SufficiencyAssessment.model_validate(
            backend(request.query, request.evidence_ids).model_dump(mode="python")
        )
    except Exception as exc:
        return CheckEvidenceSufficiencyResult(
            call=_backend_failure(
                tool_call_id=tool_call_id,
                tool_name="check_evidence_sufficiency",
                started_at=started_at,
                exc=exc,
            ),
            assessment=None,
        )

    return CheckEvidenceSufficiencyResult(
        call=ToolCallRecord(
            tool_call_id=tool_call_id,
            tool_name="check_evidence_sufficiency",
            status="success",
            latency_ms=_latency_ms(started_at),
        ),
        assessment=assessment,
    )


def validate_citations(
    request: ValidateCitationsRequest,
    *,
    tool_call_id: str,
) -> ValidateCitationsResult:
    """Deterministically reject unknown or duplicated evidence references."""

    started_at = perf_counter()
    known_ids = set(request.known_evidence_ids)
    counts = Counter(request.cited_evidence_ids)

    unknown_evidence_ids = sorted(
        evidence_id for evidence_id in counts if evidence_id not in known_ids
    )
    duplicate_evidence_ids = sorted(
        evidence_id for evidence_id, count in counts.items() if count > 1
    )

    return ValidateCitationsResult(
        call=ToolCallRecord(
            tool_call_id=tool_call_id,
            tool_name="validate_citations",
            status="success",
            latency_ms=_latency_ms(started_at),
        ),
        valid=not unknown_evidence_ids and not duplicate_evidence_ids,
        unknown_evidence_ids=unknown_evidence_ids,
        duplicate_evidence_ids=duplicate_evidence_ids,
    )


def compare_sources(
    request: CompareSourcesRequest,
    *,
    backend: SourceComparisonBackend,
    tool_call_id: str,
) -> CompareSourcesResult:
    """Execute structured source comparison through an injected backend."""

    started_at = perf_counter()
    try:
        comparisons = [
            SourceComparisonRecord.model_validate(item.model_dump(mode="python"))
            for item in backend(request.evidence_ids)
        ]
    except Exception as exc:
        return CompareSourcesResult(
            call=_backend_failure(
                tool_call_id=tool_call_id,
                tool_name="compare_sources",
                started_at=started_at,
                exc=exc,
            ),
            comparisons=[],
        )

    return CompareSourcesResult(
        call=ToolCallRecord(
            tool_call_id=tool_call_id,
            tool_name="compare_sources",
            status="success",
            latency_ms=_latency_ms(started_at),
        ),
        comparisons=comparisons,
    )
