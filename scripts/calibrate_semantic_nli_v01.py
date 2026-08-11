"""Calibrate an NLI verifier on frozen semantic match pairs."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import yaml
from sentence_transformers import CrossEncoder

ROOT = Path(__file__).resolve().parents[1]

CONFIG_PATH = ROOT / "configs" / "semantic_nli_v0_1.yaml"

OUTPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_nli_calibration_v0_1.json"


def safe_div(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def probabilities(
    scores: np.ndarray,
) -> np.ndarray:
    if (
        np.all(scores >= 0.0)
        and np.all(scores <= 1.0)
        and np.allclose(
            scores.sum(axis=1),
            1.0,
            atol=1e-4,
        )
    ):
        return scores

    shifted = scores - scores.max(
        axis=1,
        keepdims=True,
    )

    exp_scores = np.exp(shifted)

    return exp_scores / exp_scores.sum(
        axis=1,
        keepdims=True,
    )


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    dataset_path = ROOT / str(config["calibration_dataset"])

    rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    model_name = str(config["model_name"])

    device = str(config["device"])

    batch_size = int(config["batch_size"])

    model = CrossEncoder(
        model_name,
        device=device,
    )

    id2label = {
        int(key): str(value).casefold() for key, value in model.model.config.id2label.items()
    }

    entailment_indices = [index for index, label in id2label.items() if "entail" in label]

    if len(entailment_indices) != 1:
        raise RuntimeError("Could not identify exactly one entailment label.")

    entailment_index = entailment_indices[0]

    pairs = [
        (
            str(row["candidate_text"]),
            str(row["reference_text"]),
        )
        for row in rows
    ]

    raw_scores = np.asarray(
        model.predict(
            pairs,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
        ),
        dtype=float,
    )

    if raw_scores.ndim != 2 or raw_scores.shape[0] != len(rows):
        raise RuntimeError(f"Unexpected NLI score shape: {raw_scores.shape}")

    probs = probabilities(raw_scores)

    entailment_scores = probs[:, entailment_index]

    truth = np.asarray(
        [row["label"] == "MATCH" for row in rows],
        dtype=bool,
    )

    unique_scores = sorted({float(score) for score in entailment_scores})

    thresholds = [
        unique_scores[0] - 1e-6,
        *[(left + right) / 2.0 for left, right in itertools.pairwise(unique_scores)],
        unique_scores[-1] + 1e-6,
    ]

    metrics = []

    for threshold in thresholds:
        predicted = entailment_scores >= threshold

        tp = int(np.sum(predicted & truth))

        fp = int(np.sum(predicted & ~truth))

        tn = int(np.sum(~predicted & ~truth))

        fn = int(np.sum(~predicted & truth))

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

        metrics.append(
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
        metrics,
        key=lambda row: (
            row["balanced_accuracy"],
            min(
                row["recall"],
                row["specificity"],
            ),
            row["precision"],
        ),
    )

    acceptance = config["acceptance_criteria"]

    acceptance_pass = (
        best["balanced_accuracy"] >= float(acceptance["minimum_balanced_accuracy"])
        and best["recall"] >= float(acceptance["minimum_recall"])
        and best["specificity"] >= float(acceptance["minimum_specificity"])
    )

    scored_pairs = []

    for row, score, probabilities_row in zip(
        rows,
        entailment_scores,
        probs,
        strict=True,
    ):
        scored_pairs.append(
            {
                **row,
                "entailment_probability": (float(score)),
                "nli_probabilities": {
                    id2label[index]: float(probabilities_row[index])
                    for index in range(len(probabilities_row))
                },
            }
        )

    report = {
        "version": "v0.1",
        "model_name": model_name,
        "model_commit": getattr(
            model.model.config,
            "_commit_hash",
            None,
        ),
        "device": device,
        "pair_count": len(rows),
        "label_mapping": id2label,
        "entailment_index": (entailment_index),
        "recommended_threshold": (best["threshold"]),
        "recommended_metrics": best,
        "acceptance_criteria": (acceptance),
        "acceptance_pass": (acceptance_pass),
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

    print("model:", model_name)
    print(
        "model commit:",
        report["model_commit"],
    )
    print(
        "label mapping:",
        id2label,
    )
    print("pairs:", len(rows))
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
        "acceptance pass:",
        acceptance_pass,
    )
    print(
        "threshold frozen:",
        False,
    )
    print(
        "report:",
        OUTPUT_PATH,
    )


if __name__ == "__main__":
    main()
