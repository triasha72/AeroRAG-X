"""Tests for frozen-plan LoRA training-example construction."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aeroragx.generation.provider import (
    ProviderClaim,
    ProviderEvidence,
    ProviderResponse,
    StaticGenerationProvider,
)
from aeroragx.generation.structured_provider import (
    StructuredModelRequest,
    StructuredModelResult,
)
from aeroragx.processing.chunking import (
    ChunkRecord,
)
from aeroragx.training.builder import (
    REFUSAL_TARGET_ANSWER,
    ExampleBuildError,
    TrainingExampleBuilder,
)
from aeroragx.training.planning import (
    PlannedExample,
)
from aeroragx.training.teacher import (
    StructuredTeacherClient,
    TeacherConfig,
    TeacherProviderConfig,
    TeacherQuestionConfig,
    TeacherRefusalConfig,
    TeacherSupportedConfig,
)


class QueueTransport:
    """Deterministic fake teacher transport."""

    def __init__(
        self,
        outcomes: Sequence[StructuredModelResult | Exception],
    ) -> None:
        self._outcomes = list(outcomes)

        self.requests: list[StructuredModelRequest] = []

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        """Return the next queued structured result."""

        del timeout_seconds

        self.requests.append(request)

        if not self._outcomes:
            raise AssertionError("Fake teacher transport has no queued outcome.")

        outcome = self._outcomes.pop(0)

        if isinstance(
            outcome,
            Exception,
        ):
            raise outcome

        return outcome


def make_chunk(
    *,
    document_id: int,
    chunk_index: int,
) -> ChunkRecord:
    """Build one deterministic processed-corpus chunk."""

    text = (
        f"Technical content for document "
        f"{document_id}, chunk {chunk_index}. "
        "The engineering system includes "
        "thermal transport, component sizing, "
        "performance constraints, and "
        "aircraft-level integration considerations."
    )

    return ChunkRecord(
        chunk_id=(f"{document_id}:chunk:{chunk_index:05d}"),
        document_id=(document_id),
        chunk_index=(chunk_index),
        page_start=1,
        page_end=1,
        page_ids=[f"{document_id}:page:00001"],
        text=text,
        word_count=len(text.split()),
        character_count=len(text),
        token_estimate=len(text.split()),
        citation_url=(f"https://example.test/citation/{document_id}"),
        source_url=(f"https://example.test/source/{document_id}"),
        document_sha256=(f"{document_id:064d}"),
    )


def make_chunks() -> list[ChunkRecord]:
    """Build deterministic corpus fixtures."""

    return [
        make_chunk(
            document_id=1001,
            chunk_index=0,
        ),
        make_chunk(
            document_id=1001,
            chunk_index=1,
        ),
        make_chunk(
            document_id=1001,
            chunk_index=2,
        ),
        make_chunk(
            document_id=1002,
            chunk_index=0,
        ),
    ]


def make_teacher_config(
    *,
    max_draft_attempts: int = 3,
) -> TeacherConfig:
    """Build teacher configuration without touching a network."""

    return TeacherConfig(
        version="0.1",
        provider=(
            TeacherProviderConfig(
                generation_config=("generation.yaml"),
                provider_config=("provider.yaml"),
                http_transport_config=("http.yaml"),
                provider_runtime_config=("runtime.yaml"),
                teacher_schema_name=("teacher-test"),
            )
        ),
        question_generation=(
            TeacherQuestionConfig(
                timeout_seconds=30.0,
                max_retries=0,
                retry_backoff_seconds=0.0,
                max_draft_attempts=(max_draft_attempts),
                minimum_characters=25,
                maximum_characters=320,
            )
        ),
        ordinary=(TeacherSupportedConfig(max_claims=4)),
        synthesis=(TeacherSupportedConfig(max_claims=6)),
        refusal=(TeacherRefusalConfig(validation_enabled=True)),
    )


def make_plan(
    *,
    plan_id: str = "plan_0001",
    example_type: str = "ordinary",
    document_id: int = 1001,
    chunk_ids: list[str] | None = None,
) -> PlannedExample:
    """Build one frozen example-plan fixture."""

    resolved_chunk_ids = (
        chunk_ids
        if chunk_ids is not None
        else [
            "1001:chunk:00000",
            "1001:chunk:00001",
        ]
    )

    return PlannedExample(
        plan_id=plan_id,
        example_type=example_type,
        document_id=document_id,
        chunk_ids=(resolved_chunk_ids),
        evidence_word_count=200,
    )


def make_question_result(
    question: str,
) -> StructuredModelResult:
    """Build one teacher question result."""

    return StructuredModelResult(
        payload={
            "question": question,
        },
        request_id="question-request",
    )


def make_verification_result(
    *,
    supported: bool,
) -> StructuredModelResult:
    """Build one refusal-support result."""

    return StructuredModelResult(
        payload={
            "supported_by_evidence": (supported),
            "missing_information": (
                None
                if supported
                else ("The evidence does not state the requested certification threshold.")
            ),
        },
        request_id=("verification-request"),
    )


def make_supported_response() -> ProviderResponse:
    """Build a valid ordinary response."""

    return ProviderResponse(
        answer=("The system transports and rejects waste heat."),
        claims=[
            ProviderClaim(
                text=("The system transports waste heat."),
                evidence_ids=["E1"],
            ),
            ProviderClaim(
                text=("The system also supports heat rejection."),
                evidence_ids=["E2"],
            ),
        ],
        insufficient_evidence=False,
    )


def make_builder(
    *,
    teacher_outcomes: Sequence[StructuredModelResult | Exception],
    answer_response: (ProviderResponse | None) = None,
    selected_document_ids: set[int] | None = None,
    protected_document_ids: set[int] | None = None,
    max_draft_attempts: int = 3,
    chunks: list[ChunkRecord] | None = None,
) -> tuple[
    TrainingExampleBuilder,
    StaticGenerationProvider,
    QueueTransport,
]:
    """Build a fully offline training-example builder."""

    transport = QueueTransport(teacher_outcomes)

    client = StructuredTeacherClient(
        model_name="teacher-test",
        transport=transport,
        timeout_seconds=30.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
    )

    provider = StaticGenerationProvider(
        answer_response if answer_response is not None else make_supported_response()
    )

    builder = TrainingExampleBuilder(
        chunks=(chunks if chunks is not None else make_chunks()),
        selected_document_ids=(
            selected_document_ids if selected_document_ids is not None else {1001}
        ),
        protected_document_ids=(
            protected_document_ids if protected_document_ids is not None else set()
        ),
        teacher_config=(make_teacher_config(max_draft_attempts=(max_draft_attempts))),
        question_client=client,
        answer_provider=provider,
    )

    return (
        builder,
        provider,
        transport,
    )


def test_ordinary_example_preserves_frozen_chunk_order() -> None:
    builder, provider, _ = make_builder(
        teacher_outcomes=[
            make_question_result("How does the architecture transport and reject waste heat?")
        ]
    )

    plan = make_plan(
        chunk_ids=[
            "1001:chunk:00002",
            "1001:chunk:00000",
        ]
    )

    result = builder.build(plan)

    assert result.example.example_id == "train_plan_0001"

    assert result.example.query == ("How does the architecture transport and reject waste heat?")

    assert [evidence.evidence_id for evidence in result.example.evidence] == [
        "E1",
        "E2",
    ]

    assert [evidence.chunk_id for evidence in result.example.evidence] == [
        "1001:chunk:00002",
        "1001:chunk:00000",
    ]

    assert provider.received_max_claims == [4]


def test_missing_planned_chunk_is_rejected() -> None:
    builder, _, _ = make_builder(teacher_outcomes=[])

    plan = make_plan(
        chunk_ids=[
            "1001:chunk:99999",
            "1001:chunk:00000",
        ]
    )

    with pytest.raises(
        ExampleBuildError,
        match=("does not exist"),
    ):
        builder.build(plan)


def test_wrong_document_chunk_is_rejected() -> None:
    builder, _, _ = make_builder(teacher_outcomes=[])

    plan = make_plan(
        chunk_ids=[
            "1001:chunk:00000",
            "1002:chunk:00000",
        ]
    )

    with pytest.raises(
        ExampleBuildError,
        match=("belongs to document 1002"),
    ):
        builder.build(plan)


def test_unselected_document_is_rejected() -> None:
    builder, _, _ = make_builder(teacher_outcomes=[])

    plan = make_plan(
        document_id=1002,
        chunk_ids=[
            "1002:chunk:00000",
        ],
    )

    with pytest.raises(
        ExampleBuildError,
        match=("not part of the frozen"),
    ):
        builder.build(plan)


def test_selected_protected_overlap_is_rejected_at_initialization() -> None:
    with pytest.raises(
        ValueError,
        match=("overlap the protected"),
    ):
        make_builder(
            teacher_outcomes=[],
            selected_document_ids={1001},
            protected_document_ids={1001},
        )


def test_synthesis_requires_at_least_two_claims() -> None:
    response = ProviderResponse(
        answer=("The system has one supported result."),
        claims=[
            ProviderClaim(
                text=("One supported result."),
                evidence_ids=["E1"],
            )
        ],
        insufficient_evidence=False,
    )

    builder, _, _ = make_builder(
        teacher_outcomes=[
            make_question_result(
                "How do the thermal "
                "transport and sizing "
                "considerations interact "
                "in the architecture?"
            )
        ],
        answer_response=response,
        max_draft_attempts=1,
    )

    plan = make_plan(
        example_type="synthesis",
        chunk_ids=[
            "1001:chunk:00000",
            "1001:chunk:00001",
            "1001:chunk:00002",
        ],
    )

    with pytest.raises(
        ExampleBuildError,
        match=("at least two claims"),
    ):
        builder.build(plan)


def test_synthesis_requires_multiple_evidence_ids() -> None:
    response = ProviderResponse(
        answer=("Two claims are present but use one evidence item."),
        claims=[
            ProviderClaim(
                text="First claim.",
                evidence_ids=["E1"],
            ),
            ProviderClaim(
                text="Second claim.",
                evidence_ids=["E1"],
            ),
        ],
        insufficient_evidence=False,
    )

    builder, _, _ = make_builder(
        teacher_outcomes=[
            make_question_result(
                "How do multiple engineering considerations shape the architecture?"
            )
        ],
        answer_response=response,
        max_draft_attempts=1,
    )

    plan = make_plan(
        example_type="synthesis",
        chunk_ids=[
            "1001:chunk:00000",
            "1001:chunk:00001",
            "1001:chunk:00002",
        ],
    )

    with pytest.raises(
        ExampleBuildError,
        match=("two distinct evidence IDs"),
    ):
        builder.build(plan)


def test_refusal_uses_deterministic_target_without_answer_call() -> None:
    builder, provider, _ = make_builder(
        teacher_outcomes=[
            make_question_result(
                "What exact certification temperature threshold must this architecture satisfy?"
            ),
            make_verification_result(supported=False),
        ]
    )

    plan = make_plan(
        example_type="refusal",
    )

    result = builder.build(plan)

    assert result.example.response.answer == REFUSAL_TARGET_ANSWER

    assert result.example.response.claims == []

    assert result.example.response.insufficient_evidence is True

    assert provider.call_count == 0

    assert len(result.verification_telemetry) == 1


def test_refusal_redrafts_when_first_question_is_supported() -> None:
    builder, provider, _ = make_builder(
        teacher_outcomes=[
            make_question_result(
                "How does the system transport waste heat through its cooling loop?"
            ),
            make_verification_result(supported=True),
            make_question_result(
                "What exact certification temperature threshold must the cooling loop satisfy?"
            ),
            make_verification_result(supported=False),
        ]
    )

    plan = make_plan(
        example_type="refusal",
    )

    result = builder.build(plan)

    assert result.question_attempts == 2

    assert len(result.verification_telemetry) == 2

    assert result.example.query == (
        "What exact certification temperature threshold must the cooling loop satisfy?"
    )

    assert provider.call_count == 0


def test_refusal_fails_when_every_draft_is_supported() -> None:
    builder, _, _ = make_builder(
        teacher_outcomes=[
            make_question_result("How does the cooling loop transport waste heat?"),
            make_verification_result(supported=True),
            make_question_result("How does the radiator reject transported heat?"),
            make_verification_result(supported=True),
        ],
        max_draft_attempts=2,
    )

    plan = make_plan(
        example_type="refusal",
    )

    with pytest.raises(
        ExampleBuildError,
        match=("verified unsupported"),
    ):
        builder.build(plan)


def test_synthesis_redrafts_after_invalid_question() -> None:
    response = ProviderResponse(
        answer=(
            "Thermal transport, component sizing, "
            "and integration considerations interact "
            "across the architecture."
        ),
        claims=[
            ProviderClaim(
                text=("Thermal transport affects the architecture."),
                evidence_ids=["E1"],
            ),
            ProviderClaim(
                text=("Component sizing and integration also affect the architecture."),
                evidence_ids=[
                    "E2",
                    "E3",
                ],
            ),
        ],
        insufficient_evidence=False,
    )

    builder, _, transport = make_builder(
        teacher_outcomes=[
            make_question_result(
                "Based on the supplied excerpts, how do the engineering factors interact?"
            ),
            make_question_result(
                "How do thermal transport, component sizing, "
                "and integration constraints interact "
                "within the architecture?"
            ),
        ],
        answer_response=response,
    )

    plan = make_plan(
        example_type="synthesis",
        chunk_ids=[
            "1001:chunk:00000",
            "1001:chunk:00001",
            "1001:chunk:00002",
        ],
    )

    result = builder.build(plan)

    assert result.question_attempts == 2

    assert result.example.query == (
        "How do thermal transport, component sizing, "
        "and integration constraints interact "
        "within the architecture?"
    )

    assert len(transport.requests) == 2

    assert "previous draft was rejected" in (transport.requests[1].user_prompt.casefold())


class QueueGenerationProviderForRepair:
    """Return deterministic generation responses in order."""

    def __init__(
        self,
        responses: Sequence[ProviderResponse],
    ) -> None:
        self._responses = list(responses)

        self.received_queries: list[str] = []

    @property
    def call_count(
        self,
    ) -> int:
        """Return generation-call count."""

        return len(self.received_queries)

    def generate(
        self,
        *,
        query: str,
        evidence: Sequence[ProviderEvidence],
        max_claims: int,
    ) -> ProviderResponse:
        """Return the next queued response."""

        del evidence
        del max_claims

        self.received_queries.append(query)

        if not self._responses:
            raise AssertionError("Queue generation provider has no queued response.")

        return self._responses.pop(0).model_copy(deep=True)


def test_synthesis_repairs_single_evidence_answer() -> None:
    first_response = ProviderResponse(
        answer=("The first answer contains two claims but relies on only one evidence item."),
        claims=[
            ProviderClaim(
                text=("Thermal transport affects the architecture."),
                evidence_ids=["E1"],
            ),
            ProviderClaim(
                text=("Thermal constraints also affect integration."),
                evidence_ids=["E1"],
            ),
        ],
        insufficient_evidence=False,
    )

    repaired_response = ProviderResponse(
        answer=("Thermal transport and component sizing jointly shape system integration."),
        claims=[
            ProviderClaim(
                text=("Thermal transport affects integration."),
                evidence_ids=["E1"],
            ),
            ProviderClaim(
                text=("Component sizing also affects integration."),
                evidence_ids=["E2"],
            ),
        ],
        insufficient_evidence=False,
    )

    transport = QueueTransport(
        [
            make_question_result("How does thermal transport affect the architecture?"),
            make_question_result(
                "How do thermal transport and component sizing jointly shape system integration?"
            ),
        ]
    )

    question_client = StructuredTeacherClient(
        model_name="teacher-test",
        transport=transport,
        timeout_seconds=30.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
    )

    provider = QueueGenerationProviderForRepair(
        [
            first_response,
            repaired_response,
        ]
    )

    builder = TrainingExampleBuilder(
        chunks=make_chunks(),
        selected_document_ids={1001},
        protected_document_ids=set(),
        teacher_config=(make_teacher_config(max_draft_attempts=3)),
        question_client=(question_client),
        answer_provider=provider,
    )

    plan = make_plan(
        plan_id="plan_0069",
        example_type="synthesis",
        chunk_ids=[
            "1001:chunk:00000",
            "1001:chunk:00001",
            "1001:chunk:00002",
        ],
    )

    result = builder.build(plan)

    assert provider.call_count == 2

    assert result.question_attempts == 2

    assert result.example.query == (
        "How do thermal transport and component sizing jointly shape system integration?"
    )

    cited_evidence_ids = {
        evidence_id
        for claim in result.example.response.claims
        for evidence_id in claim.evidence_ids
    }

    assert cited_evidence_ids == {
        "E1",
        "E2",
    }

    assert "synthesis repair requirement" in (transport.requests[1].user_prompt.casefold())
