from aeroragx.evaluation.qasper import answerable_questions, evidence_indices, paper_paragraphs


def test_evidence_matching_normalizes_whitespace_and_case() -> None:
    paragraphs = ["A first paragraph.", "Human   Evidence appears HERE."]
    assert evidence_indices(paragraphs, ["human evidence appears here."]) == frozenset({1})


def test_answerable_questions_keep_human_annotation_count() -> None:
    paper = {
        "full_text": [{"section_name": "x", "paragraphs": ["The evidence paragraph."]}],
        "qas": [
            {
                "question_id": "q1",
                "question": "What is the evidence?",
                "answers": [
                    {"answer": {"unanswerable": False, "evidence": ["The evidence paragraph."]}},
                    {"answer": {"unanswerable": False, "evidence": ["The evidence paragraph."]}},
                ],
            }
        ],
    }
    assert paper_paragraphs(paper) == ["The evidence paragraph."]
    questions = answerable_questions(paper)
    assert questions[0].annotation_count == 2
    assert questions[0].evidence_paragraph_indices == frozenset({0})
