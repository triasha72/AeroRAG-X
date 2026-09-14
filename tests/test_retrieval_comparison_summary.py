import pytest

from scripts.summarize_retrieval_comparison import summarize


def _artifact(path, name: str, count: int, score: float) -> None:
    path.write_text(
        '{"model_name":"' + name + '","query_count":' + str(count)
        + ',"recall_at_5":' + str(score) + ',"recall_at_10":' + str(score)
        + ',"mrr_at_10":' + str(score) + ',"ndcg_at_10":' + str(score) + '}',
        encoding="utf-8",
    )


def test_summarize_requires_matching_frozen_query_counts(tmp_path) -> None:
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    _artifact(first, "bm25", 8, 0.2)
    _artifact(second, "dense", 9, 0.3)
    with pytest.raises(ValueError, match="same query count"):
        summarize([first, second])


def test_summarize_records_metric_winners(tmp_path) -> None:
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    _artifact(first, "bm25", 8, 0.2)
    _artifact(second, "hybrid", 8, 0.3)
    result = summarize([first, second])
    assert result["query_count"] == 8
    assert result["best_method_by_metric"]["ndcg_at_10"] == "hybrid"
