from aeroragx.evaluation.public_evidence import assess_public_evidence


def test_public_evidence_passes_without_claiming_independent_aerospace_review() -> None:
    result = assess_public_evidence(
        {"any_evidence_recall_at_k": {"20": 0.91}},
        {"any_evidence_document_recall_at_k": {"10": 0.75}},
        {"case_count": 50, "complete": True, "reviewer_role": "project_author"},
    )
    assert result["decision"] == "supported"
    assert "author-reviewed" in result["non_claims"][0]


def test_public_evidence_blocks_missing_scifact() -> None:
    result = assess_public_evidence({"any_evidence_recall_at_k": {"20": 0.91}}, None, None)
    assert result["decision"] == "blocked"
