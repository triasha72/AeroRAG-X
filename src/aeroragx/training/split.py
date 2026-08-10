"""Deterministic document-aware splitting for LoRA training data."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from aeroragx.training.dataset import (
    TrainingExample,
)


class TrainingSplit(BaseModel):
    """Deterministic train/dev split."""

    model_config = ConfigDict(
        extra="forbid",
    )

    train: list[TrainingExample]
    dev: list[TrainingExample]

    @property
    def train_document_ids(self) -> set[int]:
        """Return all source documents used by training."""

        return {
            document_id for example in self.train for document_id in (example.source_document_ids)
        }

    @property
    def dev_document_ids(self) -> set[int]:
        """Return all source documents used by development."""

        return {
            document_id for example in self.dev for document_id in (example.source_document_ids)
        }


def split_training_examples(
    examples: Sequence[TrainingExample],
    *,
    dev_fraction: float = 0.10,
    seed: int = 20260810,
) -> TrainingSplit:
    """Split examples while keeping linked documents together."""

    if not examples:
        raise ValueError("Training split requires at least one example.")

    if not 0.0 <= dev_fraction <= 1.0:
        raise ValueError("dev_fraction must be between 0 and 1.")

    copied_examples = list(examples)

    example_ids = [example.example_id for example in copied_examples]

    if len(example_ids) != len(set(example_ids)):
        raise ValueError("Training split received duplicate example IDs.")

    parent = list(range(len(copied_examples)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]

            index = parent[index]

        return index

    def union(
        left: int,
        right: int,
    ) -> None:
        left_root = find(left)
        right_root = find(right)

        if left_root == right_root:
            return

        if left_root < right_root:
            parent[right_root] = left_root

        else:
            parent[left_root] = right_root

    first_example_by_document: dict[
        int,
        int,
    ] = {}

    for index, example in enumerate(copied_examples):
        for document_id in example.source_document_ids:
            previous_index = first_example_by_document.get(document_id)

            if previous_index is None:
                first_example_by_document[document_id] = index

                continue

            union(
                index,
                previous_index,
            )

    components: dict[
        int,
        list[TrainingExample],
    ] = {}

    for index, example in enumerate(copied_examples):
        root = find(index)

        components.setdefault(
            root,
            [],
        ).append(example)

    train: list[TrainingExample] = []
    dev: list[TrainingExample] = []

    for component in components.values():
        component_documents = sorted(
            {document_id for example in component for document_id in (example.source_document_ids)}
        )

        component_key = ",".join(str(document_id) for document_id in component_documents)

        score = _stable_fraction(
            seed=seed,
            component_key=component_key,
        )

        destination = dev if score < dev_fraction else train

        destination.extend(component)

    train.sort(key=lambda example: example.example_id)

    dev.sort(key=lambda example: example.example_id)

    split = TrainingSplit(
        train=train,
        dev=dev,
    )

    assert_document_disjoint(split)

    return split


def assert_document_disjoint(
    split: TrainingSplit,
) -> None:
    """Reject source-document overlap between train and dev."""

    overlap = split.train_document_ids & split.dev_document_ids

    if overlap:
        raise ValueError(
            "Train/dev source-document overlap detected: "
            + ", ".join(str(document_id) for document_id in sorted(overlap))
        )


def _stable_fraction(
    *,
    seed: int,
    component_key: str,
) -> float:
    """Map one component deterministically into [0, 1)."""

    digest = hashlib.sha256(f"{seed}:{component_key}".encode()).digest()

    integer = int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )

    return integer / float(2**64)
