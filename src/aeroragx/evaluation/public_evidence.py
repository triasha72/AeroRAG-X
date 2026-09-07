"""Research-evidence gate backed by public human annotations and an author audit."""

from __future__ import annotations

from typing import Any


def assess_public_evidence(
    qasper: dict[str, Any] | None,
    scifact: dict[str, Any] | None,
    author_audit: dict[str, Any] | None,
    trec_rag: dict[str, Any] | None = None,
    citation_corruption: dict[str, Any] | None = None,
) -> dict[str, Any]:
    qasper_recall = None if qasper is None else qasper["any_evidence_recall_at_k"].get("20")
    scifact_recall = (
        None if scifact is None else scifact["any_evidence_document_recall_at_k"].get("10")
    )
    audit_cases = None if author_audit is None else author_audit.get("case_count")
    audit_complete = None if author_audit is None else author_audit.get("complete")
    audit_role = None if author_audit is None else author_audit.get("reviewer_role")
    trec_retrieval_rows = (
        None if trec_rag is None else trec_rag.get("retrieval", {}).get("judgment_rows")
    )
    trec_citation_rows = (
        None if trec_rag is None else trec_rag.get("citations", {}).get("judgment_rows")
    )
    corruption_cases = (
        None if citation_corruption is None else citation_corruption.get("case_count")
    )
    corruption_rate = (
        None if citation_corruption is None else citation_corruption.get("detection_rate")
    )
    checks = {
        "qasper_any_evidence_recall_at_20": {
            "value": qasper_recall,
            "minimum": 0.85,
            "passed": qasper_recall is not None and qasper_recall >= 0.85,
        },
        "scifact_any_document_recall_at_10": {
            "value": scifact_recall,
            "minimum": 0.70,
            "passed": scifact_recall is not None and scifact_recall >= 0.70,
        },
        "author_error_audit": {
            "value": audit_cases,
            "minimum": 50,
            "passed": audit_cases is not None and audit_cases >= 50 and audit_complete is True,
        },
        "author_role_disclosed": {
            "value": audit_role,
            "required": "project_author",
            "passed": audit_role == "project_author",
        },
        "trec_rag_public_judgments": {
            "value": {
                "retrieval": trec_retrieval_rows,
                "citation_support": trec_citation_rows,
            },
            "minimum": {"retrieval": 20_000, "citation_support": 2_000},
            "passed": (
                trec_retrieval_rows is not None
                and trec_retrieval_rows >= 20_000
                and trec_citation_rows is not None
                and trec_citation_rows >= 2_000
            ),
        },
        "citation_provenance_corruption": {
            "value": {"cases": corruption_cases, "detection_rate": corruption_rate},
            "minimum": {"cases": 200, "detection_rate": 1.0},
            "passed": (
                corruption_cases is not None and corruption_cases >= 200 and corruption_rate == 1.0
            ),
        },
    }
    return {
        "schema_version": "1.0",
        "policy": "aeroragx-public-human-evidence-v1",
        "decision": "supported" if all(check["passed"] for check in checks.values()) else "blocked",
        "checks": checks,
        "claim_scope": (
            "offline retrieval against public human annotations plus deterministic "
            "citation-provenance failure tests"
        ),
        "non_claims": [
            "The aerospace error audit is author-reviewed, not independently reviewed.",
            "This does not establish production or safety-critical fitness.",
        ],
    }
