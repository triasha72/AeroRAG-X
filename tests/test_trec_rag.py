import json
from pathlib import Path

from aeroragx.evaluation.trec_rag import summarize_trec_rag


def test_summarizes_official_judgment_shapes(tmp_path: Path) -> None:
    topics = tmp_path / "topics.txt"
    qrels = tmp_path / "qrels.txt"
    citations = tmp_path / "citations.jsonl"
    topics.write_text("q1\tHow does the system work?\n")
    qrels.write_text("q1 0 passage-a 2\nq1 0 passage-b 0\n")
    citations.write_text(
        json.dumps(
            {
                "topic_id": "q1",
                "run_id": "run-a",
                "sentences": [
                    {"citations": [{"reference": "passage-a", "support": "2"}]}
                ],
            }
        )
        + "\n"
    )
    result = summarize_trec_rag(topics, qrels, citations)
    assert result["retrieval"]["judgment_rows"] == 2
    assert result["citations"]["support_labels"] == {"2": 1}
    assert result["evidence_role"] == "external_public_human_judgments"
