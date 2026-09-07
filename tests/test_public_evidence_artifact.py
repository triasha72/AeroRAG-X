import json
from pathlib import Path


def test_checked_in_scifact_result_and_public_evidence_boundary() -> None:
    root = Path(__file__).parents[1]
    scifact = json.loads(
        (root / "artifacts/evaluation/scifact_external_retrieval_v1.json").read_text()
    )
    assessment = json.loads(
        (root / "artifacts/evaluation/public_evidence_assessment_v1.json").read_text()
    )
    assert scifact["evaluated_claims"] == 188
    assert scifact["any_evidence_document_recall_at_k"]["10"] > 0.89
    assert assessment["checks"]["scifact_any_document_recall_at_10"]["passed"]
    assert assessment["checks"]["trec_rag_public_judgments"]["passed"]
    assert assessment["checks"]["citation_provenance_corruption"]["passed"]
    assert assessment["decision"] == "blocked"
    assert not assessment["checks"]["author_error_audit"]["passed"]
