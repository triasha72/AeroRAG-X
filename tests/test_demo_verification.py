import pytest

from aeroragx.demo_verification import verify_demo_response


def test_verifies_supported_claims_have_known_citations() -> None:
    receipt = verify_demo_response(
        {
            "insufficient_evidence": False,
            "claims": [{"citation_ids": ["C1"]}],
            "citations": [{"citation_id": "C1"}],
            "source_documents": [{"document_id": 1}],
        }
    )
    assert receipt["outcome"] == "supported_answer"
    assert receipt["citation_count"] == 1


def test_rejects_an_uncited_supported_claim() -> None:
    with pytest.raises(ValueError, match="cite"):
        verify_demo_response(
            {
                "insufficient_evidence": False,
                "claims": [{"citation_ids": []}],
                "citations": [],
                "source_documents": [],
            }
        )


def test_verifies_a_claim_free_grounded_refusal() -> None:
    receipt = verify_demo_response(
        {"insufficient_evidence": True, "claims": [], "citations": [], "source_documents": []}
    )
    assert receipt == {"outcome": "grounded_refusal", "claim_count": 0, "citation_count": 0}
