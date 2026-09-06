"""Unit tests for external NASA SME metric semantics."""

from scripts.evaluate_external_nasa_sme_bm25 import _ranking_metrics


def test_ranking_metrics_use_full_cutoff_for_ideal_ranking() -> None:
    recall, ndcg = _ranking_metrics(["a", "missing"], {"a", "b", "c"}, 10)

    assert recall == 1 / 3
    assert 0.0 < ndcg < 1.0


def test_ranking_metrics_return_zero_without_a_hit() -> None:
    recall, ndcg = _ranking_metrics(["missing"], {"a"}, 10)

    assert recall == 0.0
    assert ndcg == 0.0
