"""Deterministic evidence planning for LoRA training examples."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Collection, Sequence
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from aeroragx.processing.chunking import ChunkRecord
from aeroragx.training.selection import (
    LoRASourceSelectionManifest,
)

type ExamplePlanType = Literal[
    "ordinary",
    "synthesis",
    "refusal",
]


class ExamplePlanConfig(BaseModel):
    """Configuration for deterministic LoRA evidence planning."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(
        min_length=1,
    )

    expected_selected_document_count: int = Field(
        ge=1,
    )

    expected_selected_chunk_count: int = Field(
        ge=1,
    )

    ordinary_examples_per_document: int = Field(
        ge=1,
    )

    extra_ordinary_document_count: int = Field(
        ge=0,
    )

    synthesis_document_count: int = Field(
        ge=0,
    )

    refusal_document_count: int = Field(
        ge=0,
    )

    expected_ordinary_example_count: int = Field(
        ge=1,
    )

    expected_synthesis_example_count: int = Field(
        ge=0,
    )

    expected_refusal_example_count: int = Field(
        ge=0,
    )

    expected_total_example_count: int = Field(
        ge=1,
    )

    ordinary_evidence_chunks: int = Field(
        ge=1,
    )

    synthesis_evidence_chunks: int = Field(
        ge=1,
    )

    refusal_evidence_chunks: int = Field(
        ge=1,
    )

    minimum_chunk_words: int = Field(
        ge=1,
    )

    reference_section_prefixes: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_plan_config(
        self,
    ) -> Self:
        """Validate example-count and evidence-planning invariants."""

        if self.extra_ordinary_document_count > self.expected_selected_document_count:
            raise ValueError(
                "extra_ordinary_document_count must not exceed expected_selected_document_count."
            )

        if self.synthesis_document_count > self.expected_selected_document_count:
            raise ValueError(
                "synthesis_document_count must not exceed expected_selected_document_count."
            )

        if self.refusal_document_count > self.expected_selected_document_count:
            raise ValueError(
                "refusal_document_count must not exceed expected_selected_document_count."
            )

        expected_ordinary = (
            self.expected_selected_document_count * self.ordinary_examples_per_document
            + self.extra_ordinary_document_count
        )

        if expected_ordinary != self.expected_ordinary_example_count:
            raise ValueError(
                "expected_ordinary_example_count does not match the configured allocation."
            )

        if self.expected_synthesis_example_count != self.synthesis_document_count:
            raise ValueError(
                "The v0.1 planner creates exactly one synthesis example per synthesis document."
            )

        if self.expected_refusal_example_count != self.refusal_document_count:
            raise ValueError(
                "The v0.1 planner creates exactly one refusal example per refusal document."
            )

        expected_total = (
            self.expected_ordinary_example_count
            + self.expected_synthesis_example_count
            + self.expected_refusal_example_count
        )

        if expected_total != self.expected_total_example_count:
            raise ValueError(
                "expected_total_example_count does not match the configured type counts."
            )

        normalized_prefixes = [
            prefix.casefold().strip()
            for prefix in self.reference_section_prefixes
            if prefix.strip()
        ]

        if len(normalized_prefixes) != len(set(normalized_prefixes)):
            raise ValueError("reference_section_prefixes must not contain duplicates.")

        return self


class PlannedExample(BaseModel):
    """One frozen evidence bundle awaiting question/target generation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    plan_id: str = Field(
        min_length=1,
    )

    example_type: ExamplePlanType

    document_id: int = Field(
        ge=1,
    )

    chunk_ids: list[str] = Field(
        min_length=1,
    )

    evidence_word_count: int = Field(
        ge=1,
    )

    @model_validator(mode="after")
    def validate_plan_record(
        self,
    ) -> Self:
        """Validate one planned evidence bundle."""

        if len(self.chunk_ids) != len(set(self.chunk_ids)):
            raise ValueError("Planned example chunk IDs must be unique.")

        return self


class ExamplePlanDocumentSummary(BaseModel):
    """Per-document allocation in the frozen example plan."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    document_id: int = Field(
        ge=1,
    )

    title: str = Field(
        min_length=1,
    )

    available_chunk_count: int = Field(
        ge=1,
    )

    eligible_chunk_count: int = Field(
        ge=1,
    )

    ordinary_count: int = Field(
        ge=0,
    )

    synthesis_count: int = Field(
        ge=0,
    )

    refusal_count: int = Field(
        ge=0,
    )

    total_count: int = Field(
        ge=1,
    )

    @model_validator(mode="after")
    def validate_summary(
        self,
    ) -> Self:
        """Validate the per-document example total."""

        expected_total = self.ordinary_count + self.synthesis_count + self.refusal_count

        if self.total_count != expected_total:
            raise ValueError("Example-plan document total_count mismatch.")

        return self


class LoRAExamplePlanManifest(BaseModel):
    """Frozen evidence-bundle plan for LoRA dataset generation."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    version: str = Field(
        min_length=1,
    )

    corpus_chunks_path: str = Field(
        min_length=1,
    )

    corpus_chunks_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    source_selection_manifest_path: str = Field(
        min_length=1,
    )

    source_selection_manifest_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    protected_manifest_path: str = Field(
        min_length=1,
    )

    protected_manifest_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    plan_config_path: str = Field(
        min_length=1,
    )

    plan_config_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    selected_document_count: int = Field(
        ge=1,
    )

    selected_source_chunk_count: int = Field(
        ge=1,
    )

    planned_example_count: int = Field(
        ge=1,
    )

    ordinary_example_count: int = Field(
        ge=0,
    )

    synthesis_example_count: int = Field(
        ge=0,
    )

    refusal_example_count: int = Field(
        ge=0,
    )

    ordinary_evidence_chunks: int = Field(
        ge=1,
    )

    synthesis_evidence_chunks: int = Field(
        ge=1,
    )

    refusal_evidence_chunks: int = Field(
        ge=1,
    )

    unique_planned_chunk_count: int = Field(
        ge=1,
    )

    protected_overlap_count: int = Field(
        ge=0,
    )

    source_document_ids: list[int] = Field(
        min_length=1,
    )

    documents: list[ExamplePlanDocumentSummary] = Field(
        min_length=1,
    )

    examples: list[PlannedExample] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_manifest_consistency(
        self,
    ) -> Self:
        """Validate frozen example-plan counts and provenance."""

        if self.protected_overlap_count != 0:
            raise ValueError("A frozen example plan must have zero protected-document overlap.")

        if self.selected_document_count != len(self.source_document_ids):
            raise ValueError("selected_document_count does not match source_document_ids.")

        if self.source_document_ids != sorted(set(self.source_document_ids)):
            raise ValueError("source_document_ids must be sorted and unique.")

        if self.planned_example_count != len(self.examples):
            raise ValueError("planned_example_count does not match example records.")

        plan_ids = [example.plan_id for example in self.examples]

        if len(plan_ids) != len(set(plan_ids)):
            raise ValueError("Example-plan IDs must be unique.")

        expected_plan_ids = [
            f"plan_{index:04d}"
            for index in range(
                1,
                len(self.examples) + 1,
            )
        ]

        if plan_ids != expected_plan_ids:
            raise ValueError("Example-plan IDs must be sequential and deterministic.")

        type_counts = Counter(example.example_type for example in self.examples)

        if type_counts["ordinary"] != self.ordinary_example_count:
            raise ValueError("ordinary_example_count mismatch.")

        if type_counts["synthesis"] != self.synthesis_example_count:
            raise ValueError("synthesis_example_count mismatch.")

        if type_counts["refusal"] != self.refusal_example_count:
            raise ValueError("refusal_example_count mismatch.")

        expected_total = (
            self.ordinary_example_count + self.synthesis_example_count + self.refusal_example_count
        )

        if expected_total != self.planned_example_count:
            raise ValueError("Planned example type counts do not sum to planned_example_count.")

        evidence_sizes = {
            "ordinary": (self.ordinary_evidence_chunks),
            "synthesis": (self.synthesis_evidence_chunks),
            "refusal": (self.refusal_evidence_chunks),
        }

        valid_document_ids = set(self.source_document_ids)

        observed_document_ids: set[int] = set()

        all_chunk_ids: set[str] = set()

        for example in self.examples:
            if example.document_id not in valid_document_ids:
                raise ValueError("Example plan references a document outside source_document_ids.")

            expected_evidence_count = evidence_sizes[example.example_type]

            if len(example.chunk_ids) != expected_evidence_count:
                raise ValueError(
                    f"{example.plan_id} has "
                    f"{len(example.chunk_ids)} evidence chunks; "
                    f"expected {expected_evidence_count} "
                    f"for {example.example_type}."
                )

            observed_document_ids.add(example.document_id)

            all_chunk_ids.update(example.chunk_ids)

        if observed_document_ids != valid_document_ids:
            raise ValueError("Every selected source document must appear in the example plan.")

        if self.unique_planned_chunk_count != len(all_chunk_ids):
            raise ValueError("unique_planned_chunk_count mismatch.")

        summary_ids = [document.document_id for document in self.documents]

        if summary_ids != self.source_document_ids:
            raise ValueError("Document summaries must appear once in sorted source-document order.")

        ordinary_by_document: Counter[int] = Counter()

        synthesis_by_document: Counter[int] = Counter()

        refusal_by_document: Counter[int] = Counter()

        for example in self.examples:
            if example.example_type == "ordinary":
                ordinary_by_document[example.document_id] += 1

            elif example.example_type == "synthesis":
                synthesis_by_document[example.document_id] += 1

            else:
                refusal_by_document[example.document_id] += 1

        for summary in self.documents:
            if summary.ordinary_count != ordinary_by_document[summary.document_id]:
                raise ValueError("Document ordinary-count mismatch.")

            if summary.synthesis_count != synthesis_by_document[summary.document_id]:
                raise ValueError("Document synthesis-count mismatch.")

            if summary.refusal_count != refusal_by_document[summary.document_id]:
                raise ValueError("Document refusal-count mismatch.")

        return self


def load_example_plan_config(
    path: Path,
) -> ExamplePlanConfig:
    """Load and validate example-plan YAML."""

    try:
        raw_value = yaml.safe_load(path.read_text(encoding="utf-8"))

    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid example-plan YAML in {path}.") from exc

    try:
        return ExamplePlanConfig.model_validate(raw_value)

    except ValidationError as exc:
        raise ValueError(f"Invalid example-plan config {path}.") from exc


def load_example_plan_manifest(
    path: Path,
) -> LoRAExamplePlanManifest:
    """Load and validate a frozen example-plan manifest."""

    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))

    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid example-plan JSON in {path}.") from exc

    try:
        return LoRAExamplePlanManifest.model_validate(raw_value)

    except ValidationError as exc:
        raise ValueError(f"Invalid example-plan manifest {path}.") from exc


def write_example_plan_manifest(
    path: Path,
    manifest: LoRAExamplePlanManifest,
) -> None:
    """Write deterministic example-plan JSON."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            manifest.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_example_plan(
    chunks: Sequence[ChunkRecord],
    *,
    source_selection: LoRASourceSelectionManifest,
    protected_document_ids: Collection[int],
    config: ExamplePlanConfig,
    corpus_chunks_path: str,
    corpus_chunks_sha256: str,
    source_selection_manifest_path: str,
    source_selection_manifest_sha256: str,
    protected_manifest_path: str,
    protected_manifest_sha256: str,
    plan_config_path: str,
    plan_config_sha256: str,
) -> LoRAExamplePlanManifest:
    """Build deterministic same-document evidence bundles."""

    if source_selection.selected_document_count != config.expected_selected_document_count:
        raise ValueError(
            "Selected document count changed: "
            f"expected "
            f"{config.expected_selected_document_count}, "
            f"observed "
            f"{source_selection.selected_document_count}."
        )

    if source_selection.selected_chunk_count != config.expected_selected_chunk_count:
        raise ValueError(
            "Selected source chunk count changed: "
            f"expected "
            f"{config.expected_selected_chunk_count}, "
            f"observed "
            f"{source_selection.selected_chunk_count}."
        )

    selected_document_ids = source_selection.selected_document_id_set

    protected_overlap = sorted(selected_document_ids & set(protected_document_ids))

    if protected_overlap:
        raise ValueError(
            "Protected documents appeared in "
            "the frozen source selection: "
            + ", ".join(str(document_id) for document_id in protected_overlap)
        )

    selected_metadata = {
        document.document_id: document
        for document in source_selection.documents
        if document.status == "selected"
    }

    if set(selected_metadata) != selected_document_ids:
        raise ValueError("Source-selection metadata does not match selected_document_ids.")

    chunks_by_document: defaultdict[
        int,
        list[ChunkRecord],
    ] = defaultdict(list)

    seen_chunk_ids: set[str] = set()

    for chunk in chunks:
        if chunk.chunk_id in seen_chunk_ids:
            raise ValueError(f"Processed corpus contains duplicate chunk ID {chunk.chunk_id!r}.")

        seen_chunk_ids.add(chunk.chunk_id)

        if chunk.document_id in selected_document_ids:
            chunks_by_document[chunk.document_id].append(chunk)

    observed_selected_chunk_count = sum(
        len(chunks_by_document[document_id]) for document_id in selected_document_ids
    )

    if observed_selected_chunk_count != source_selection.selected_chunk_count:
        raise ValueError(
            "Processed corpus selected-chunk count does not match the frozen source selection."
        )

    for document_id in selected_document_ids:
        expected_chunk_count = selected_metadata[document_id].chunk_count

        observed_chunk_count = len(chunks_by_document[document_id])

        if observed_chunk_count != expected_chunk_count:
            raise ValueError(
                f"Document {document_id} expected "
                f"{expected_chunk_count} chunks but "
                f"the processed corpus contains "
                f"{observed_chunk_count}."
            )

    ranked_documents = sorted(
        selected_metadata.values(),
        key=lambda document: (
            -document.chunk_count,
            document.document_id,
        ),
    )

    extra_ordinary_ids = {
        document.document_id
        for document in ranked_documents[: config.extra_ordinary_document_count]
    }

    synthesis_ids = {
        document.document_id for document in ranked_documents[: config.synthesis_document_count]
    }

    if config.refusal_document_count == 0:
        refusal_ids: set[int] = set()

    else:
        refusal_ids = {
            document.document_id for document in ranked_documents[-config.refusal_document_count :]
        }

    eligible_by_document: dict[
        int,
        list[ChunkRecord],
    ] = {}

    for document_id in sorted(selected_document_ids):
        eligible = [
            chunk
            for chunk in sorted(
                chunks_by_document[document_id],
                key=lambda item: (
                    item.chunk_index,
                    item.chunk_id,
                ),
            )
            if _chunk_is_eligible(
                chunk,
                config=config,
            )
        ]

        ordinary_count = config.ordinary_examples_per_document + (
            1 if document_id in extra_ordinary_ids else 0
        )

        ordinary_window_count = len(eligible) - config.ordinary_evidence_chunks + 1

        if ordinary_window_count < ordinary_count:
            raise ValueError(
                f"Document {document_id} has only "
                f"{len(eligible)} eligible chunks, "
                "which is insufficient to construct "
                f"{ordinary_count} distinct ordinary "
                "evidence windows."
            )

        if document_id in synthesis_ids and len(eligible) < config.synthesis_evidence_chunks:
            raise ValueError(
                f"Document {document_id} does not have "
                "enough eligible chunks for a "
                "synthesis example."
            )

        if document_id in refusal_ids and len(eligible) < config.refusal_evidence_chunks:
            raise ValueError(
                f"Document {document_id} does not have "
                "enough eligible chunks for a "
                "refusal example."
            )

        eligible_by_document[document_id] = eligible

    examples: list[PlannedExample] = []

    summaries: list[ExamplePlanDocumentSummary] = []

    plan_counter = 1

    for document_id in sorted(selected_document_ids):
        metadata = selected_metadata[document_id]

        eligible = eligible_by_document[document_id]

        ordinary_count = config.ordinary_examples_per_document + (
            1 if document_id in extra_ordinary_ids else 0
        )

        ordinary_starts = _spaced_window_starts(
            item_count=len(eligible),
            window_size=(config.ordinary_evidence_chunks),
            window_count=(ordinary_count),
        )

        for start in ordinary_starts:
            bundle = eligible[start : start + config.ordinary_evidence_chunks]

            examples.append(
                _planned_example(
                    plan_counter=(plan_counter),
                    example_type=("ordinary"),
                    document_id=(document_id),
                    chunks=bundle,
                )
            )

            plan_counter += 1

        synthesis_count = 0

        if document_id in synthesis_ids:
            start = _center_window_start(
                item_count=len(eligible),
                window_size=(config.synthesis_evidence_chunks),
            )

            bundle = eligible[start : start + config.synthesis_evidence_chunks]

            examples.append(
                _planned_example(
                    plan_counter=(plan_counter),
                    example_type=("synthesis"),
                    document_id=(document_id),
                    chunks=bundle,
                )
            )

            plan_counter += 1

            synthesis_count = 1

        refusal_count = 0

        if document_id in refusal_ids:
            start = _refusal_window_start(
                item_count=len(eligible),
                window_size=(config.refusal_evidence_chunks),
            )

            bundle = eligible[start : start + config.refusal_evidence_chunks]

            examples.append(
                _planned_example(
                    plan_counter=(plan_counter),
                    example_type=("refusal"),
                    document_id=(document_id),
                    chunks=bundle,
                )
            )

            plan_counter += 1

            refusal_count = 1

        summaries.append(
            ExamplePlanDocumentSummary(
                document_id=(document_id),
                title=metadata.title,
                available_chunk_count=(metadata.chunk_count),
                eligible_chunk_count=len(eligible),
                ordinary_count=(ordinary_count),
                synthesis_count=(synthesis_count),
                refusal_count=(refusal_count),
                total_count=(ordinary_count + synthesis_count + refusal_count),
            )
        )

    type_counts = Counter(example.example_type for example in examples)

    if type_counts["ordinary"] != config.expected_ordinary_example_count:
        raise RuntimeError("Ordinary example-plan count mismatch.")

    if type_counts["synthesis"] != config.expected_synthesis_example_count:
        raise RuntimeError("Synthesis example-plan count mismatch.")

    if type_counts["refusal"] != config.expected_refusal_example_count:
        raise RuntimeError("Refusal example-plan count mismatch.")

    if len(examples) != config.expected_total_example_count:
        raise RuntimeError("Total example-plan count mismatch.")

    unique_chunk_ids = {chunk_id for example in examples for chunk_id in example.chunk_ids}

    return LoRAExamplePlanManifest(
        version=config.version,
        corpus_chunks_path=(corpus_chunks_path),
        corpus_chunks_sha256=(corpus_chunks_sha256),
        source_selection_manifest_path=(source_selection_manifest_path),
        source_selection_manifest_sha256=(source_selection_manifest_sha256),
        protected_manifest_path=(protected_manifest_path),
        protected_manifest_sha256=(protected_manifest_sha256),
        plan_config_path=(plan_config_path),
        plan_config_sha256=(plan_config_sha256),
        selected_document_count=(source_selection.selected_document_count),
        selected_source_chunk_count=(source_selection.selected_chunk_count),
        planned_example_count=(len(examples)),
        ordinary_example_count=(type_counts["ordinary"]),
        synthesis_example_count=(type_counts["synthesis"]),
        refusal_example_count=(type_counts["refusal"]),
        ordinary_evidence_chunks=(config.ordinary_evidence_chunks),
        synthesis_evidence_chunks=(config.synthesis_evidence_chunks),
        refusal_evidence_chunks=(config.refusal_evidence_chunks),
        unique_planned_chunk_count=(len(unique_chunk_ids)),
        protected_overlap_count=0,
        source_document_ids=sorted(selected_document_ids),
        documents=summaries,
        examples=examples,
    )


def _chunk_is_eligible(
    chunk: ChunkRecord,
    *,
    config: ExamplePlanConfig,
) -> bool:
    """Apply conservative deterministic evidence-quality filtering."""

    if chunk.word_count < config.minimum_chunk_words:
        return False

    normalized = " ".join(chunk.text.casefold().split())

    for prefix in config.reference_section_prefixes:
        normalized_prefix = " ".join(prefix.casefold().split())

        if normalized.startswith(normalized_prefix):
            return False

    return True


def _spaced_window_starts(
    *,
    item_count: int,
    window_size: int,
    window_count: int,
) -> list[int]:
    """Choose distinct windows distributed across a document."""

    maximum_start = item_count - window_size

    available_window_count = maximum_start + 1

    if available_window_count < window_count:
        raise ValueError("Not enough distinct windows for the requested allocation.")

    if window_count == 1:
        return [maximum_start // 2]

    starts = [round(index * maximum_start / (window_count - 1)) for index in range(window_count)]

    if len(starts) != len(set(starts)):
        starts = list(range(window_count))

    return starts


def _center_window_start(
    *,
    item_count: int,
    window_size: int,
) -> int:
    """Choose a central contiguous evidence window."""

    return (item_count - window_size) // 2


def _refusal_window_start(
    *,
    item_count: int,
    window_size: int,
) -> int:
    """Choose an interior evidence window for refusal planning."""

    maximum_start = item_count - window_size

    return 2 * maximum_start // 3


def _planned_example(
    *,
    plan_counter: int,
    example_type: ExamplePlanType,
    document_id: int,
    chunks: Sequence[ChunkRecord],
) -> PlannedExample:
    """Construct one deterministic plan record."""

    return PlannedExample(
        plan_id=(f"plan_{plan_counter:04d}"),
        example_type=(example_type),
        document_id=(document_id),
        chunk_ids=[chunk.chunk_id for chunk in chunks],
        evidence_word_count=sum(chunk.word_count for chunk in chunks),
    )
