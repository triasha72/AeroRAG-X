"""Propose semantically adjacent concepts for hard-negative review."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import yaml
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]

ANNOTATION_PATH = ROOT / "data" / "evaluation" / "generation_semantic_concepts_v0_1.jsonl"

CONFIG_PATH = ROOT / "configs" / "dense_v0_1.yaml"

OUTPUT_PATH = ROOT / "artifacts" / "evaluation" / "semantic_hard_negative_candidates_v0_1.json"


def main() -> None:
    rows = [
        json.loads(line)
        for line in ANNOTATION_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    concepts: dict[str, str] = {}

    for row in rows:
        for concept in row["expected_concepts"]:
            concept_id = str(concept["concept_id"])
            canonical = str(concept["canonical_text"])

            previous = concepts.get(concept_id)

            if previous is not None and previous != canonical:
                raise RuntimeError(f"Inconsistent concept {concept_id!r}")

            concepts[concept_id] = canonical

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    model = SentenceTransformer(
        str(config["model_name"]),
        device=str(config["device"]),
    )

    concept_ids = sorted(concepts)

    texts = [concepts[concept_id] for concept_id in concept_ids]

    embeddings = model.encode(
        texts,
        batch_size=32,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    candidates = []

    for left, right in itertools.combinations(
        range(len(concept_ids)),
        2,
    ):
        similarity = float(
            np.dot(
                embeddings[left],
                embeddings[right],
            )
        )

        candidates.append(
            {
                "left_concept_id": concept_ids[left],
                "left_text": texts[left],
                "right_concept_id": concept_ids[right],
                "right_text": texts[right],
                "cosine_similarity": similarity,
                "review_label": None,
            }
        )

    candidates.sort(
        key=lambda row: row["cosine_similarity"],
        reverse=True,
    )

    output = {
        "version": "v0.1",
        "model_name": str(config["model_name"]),
        "concept_count": len(concept_ids),
        "candidate_pair_count": len(candidates),
        "review_policy": (
            "High-similarity distinct concepts are "
            "candidates only. Human review is required "
            "before assigning NO_MATCH."
        ),
        "candidates": candidates,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("concepts:", len(concept_ids))
    print("candidate pairs:", len(candidates))
    print()
    print("TOP 40 ADJACENT-CONCEPT PAIRS")
    print()

    for index, row in enumerate(
        candidates[:40],
        start=1,
    ):
        print(f"{index:02d}. {row['cosine_similarity']:.4f}")
        print(
            "   ",
            row["left_concept_id"],
        )
        print(
            "      ",
            row["left_text"],
        )
        print(
            "   ",
            row["right_concept_id"],
        )
        print(
            "      ",
            row["right_text"],
        )
        print()

    print("report:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
