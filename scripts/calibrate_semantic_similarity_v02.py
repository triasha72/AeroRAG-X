"""Calibrate semantic concept similarity on frozen labeled pairs."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import yaml
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]

CALIBRATION_PATH = ROOT / "data" / "evaluation" / "semantic_match_calibration_v0_2.jsonl"

DENSE_CONFIG_PATH = ROOT / "configs" / "dense_v0_1.yaml"

OUTPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_similarity_calibration_v0_2.json"


def safe_div(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def main() -> None:
    rows = [
        json.loads(line)
        for line in CALIBRATION_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    config = yaml.safe_load(DENSE_CONFIG_PATH.read_text(encoding="utf-8"))

    model_name = str(config["model_name"])
    device = str(config["device"])

    model = SentenceTransformer(
        model_name,
        device=device,
    )

    references = [row["reference_text"] for row in rows]

    candidates = [row["candidate_text"] for row in rows]

    reference_embeddings = model.encode(
        references,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    candidate_embeddings = model.encode(
        candidates,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    similarities = np.sum(
        reference_embeddings * candidate_embeddings,
        axis=1,
    )

    labels = np.asarray(
        [row["label"] == "MATCH" for row in rows],
        dtype=bool,
    )

    unique_scores = sorted({float(score) for score in similarities})

    thresholds = [
        unique_scores[0] - 1e-6,
        *[(left + right) / 2.0 for left, right in itertools.pairwise(unique_scores)],
        unique_scores[-1] + 1e-6,
    ]

    candidates_metrics = []

    for threshold in thresholds:
        predicted = similarities >= threshold

        tp = int(np.sum(predicted & labels))
        fp = int(np.sum(predicted & ~labels))
        tn = int(np.sum(~predicted & ~labels))
        fn = int(np.sum(~predicted & labels))

        recall = safe_div(
            tp,
            tp + fn,
        )

        specificity = safe_div(
            tn,
            tn + fp,
        )

        precision = safe_div(
            tp,
            tp + fp,
        )

        balanced_accuracy = (recall + specificity) / 2.0

        candidates_metrics.append(
            {
                "threshold": threshold,
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "precision": precision,
                "recall": recall,
                "specificity": specificity,
                "balanced_accuracy": (balanced_accuracy),
            }
        )

    best = max(
        candidates_metrics,
        key=lambda row: (
            row["balanced_accuracy"],
            row["precision"],
            row["specificity"],
            row["threshold"],
        ),
    )

    match_scores = similarities[labels]
    no_match_scores = similarities[~labels]

    def summary(
        values: np.ndarray,
    ) -> dict[str, float]:
        return {
            "min": float(np.min(values)),
            "p25": float(np.quantile(values, 0.25)),
            "median": float(np.median(values)),
            "p75": float(np.quantile(values, 0.75)),
            "max": float(np.max(values)),
        }

    scored_pairs = []

    for row, score in zip(
        rows,
        similarities,
        strict=True,
    ):
        scored_pairs.append(
            {
                **row,
                "cosine_similarity": float(score),
            }
        )

    report = {
        "version": "v0.2",
        "model_name": model_name,
        "device": device,
        "pair_count": len(rows),
        "match_count": int(np.sum(labels)),
        "no_match_count": int(np.sum(~labels)),
        "match_score_summary": summary(match_scores),
        "no_match_score_summary": summary(no_match_scores),
        "recommended_threshold": (best["threshold"]),
        "recommended_metrics": best,
        "threshold_frozen": False,
        "scored_pairs": scored_pairs,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "model:",
        model_name,
    )
    print(
        "pairs:",
        len(rows),
    )
    print(
        "MATCH summary:",
        summary(match_scores),
    )
    print(
        "NO_MATCH summary:",
        summary(no_match_scores),
    )
    print(
        "recommended threshold:",
        f"{best['threshold']:.6f}",
    )
    print(
        "balanced accuracy:",
        f"{best['balanced_accuracy']:.6f}",
    )
    print(
        "precision:",
        f"{best['precision']:.6f}",
    )
    print(
        "recall:",
        f"{best['recall']:.6f}",
    )
    print(
        "specificity:",
        f"{best['specificity']:.6f}",
    )
    print(
        "confusion:",
        {
            "tp": best["tp"],
            "fp": best["fp"],
            "tn": best["tn"],
            "fn": best["fn"],
        },
    )
    print(
        "report:",
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()
