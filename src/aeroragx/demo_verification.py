"""Portable checks for a saved AeroRAG-X API response."""

from __future__ import annotations

from typing import Any


def verify_demo_response(payload: dict[str, Any]) -> dict[str, object]:
    """Check the public supported-answer and refusal contracts.

    The result deliberately keeps only counts and state, allowing it to be
    committed as a demo receipt without copying retrieved source content.
    """

    insufficient = payload.get("insufficient_evidence")
    if not isinstance(insufficient, bool):
        raise ValueError("Response must include a boolean insufficient_evidence field.")
    claims = payload.get("claims")
    citations = payload.get("citations")
    sources = payload.get("source_documents")
    if not all(isinstance(value, list) for value in (claims, citations, sources)):
        raise ValueError("Response must include claims, citations, and source_documents lists.")

    if insufficient:
        if claims or citations or sources:
            raise ValueError("A grounded refusal must not include claims or citations.")
        return {"outcome": "grounded_refusal", "claim_count": 0, "citation_count": 0}

    if not claims:
        raise ValueError("A supported response must contain at least one claim.")
    citation_ids = {
        citation.get("citation_id") for citation in citations if isinstance(citation, dict)
    }
    if None in citation_ids or len(citation_ids) != len(citations):
        raise ValueError("Every citation must include a unique citation_id.")
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("Each claim must be an object.")
        claim_citations = claim.get("citation_ids")
        if not isinstance(claim_citations, list) or not claim_citations:
            raise ValueError("Every supported claim must cite at least one source.")
        unknown = set(claim_citations) - citation_ids
        if unknown:
            raise ValueError(f"Claim references unknown citation IDs: {sorted(unknown)}")
    return {
        "outcome": "supported_answer",
        "claim_count": len(claims),
        "citation_count": len(citations),
        "source_document_count": len(sources),
    }
