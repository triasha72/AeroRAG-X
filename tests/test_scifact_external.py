import pytest

from aeroragx.evaluation.scifact import normalize_claims, normalize_corpus


def test_normalizes_scifact_human_evidence() -> None:
    documents = normalize_corpus(
        [{"doc_id": 10, "title": "Paper", "abstract": ["First.", "Evidence."]}]
    )
    claims = normalize_claims(
        [
            {
                "id": 1,
                "claim": "A scientific claim",
                "evidence": {"10": [{"label": "SUPPORT", "sentences": [1]}]},
            }
        ]
    )
    assert documents[0].abstract[1] == "Evidence."
    assert claims[0].evidence_doc_ids == (10,)
    assert claims[0].evidence_sentence_ids == {10: (1,)}


def test_rejects_empty_scifact_inputs() -> None:
    with pytest.raises(ValueError, match="No SciFact documents"):
        normalize_corpus([])
    with pytest.raises(ValueError, match="human evidence"):
        normalize_claims([{"id": 1, "claim": "no evidence", "evidence": {}}])
