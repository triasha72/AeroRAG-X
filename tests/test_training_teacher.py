"""Tests for structured LoRA training-teacher utilities."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from aeroragx.generation.provider import (
    ProviderEvidence,
)
from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)
from aeroragx.training.teacher import (
    RefusalSupportAssessment,
    StructuredTeacherClient,
    TeacherQuestionConfig,
    TeacherQuestionDraft,
    TeacherQuestionValidationError,
    build_ordinary_question_prompt,
    build_refusal_question_prompt,
    build_refusal_verification_prompt,
    build_synthesis_question_prompt,
    validate_teacher_question,
)


class QueueTransport:
    """Small deterministic fake structured transport."""

    def __init__(
        self,
        outcomes: Sequence[StructuredModelResult | Exception],
    ) -> None:
        self._outcomes = list(outcomes)

        self.requests: list[StructuredModelRequest] = []

        self.timeouts: list[float] = []

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        """Return or raise the next queued outcome."""

        self.requests.append(request)

        self.timeouts.append(timeout_seconds)

        if not self._outcomes:
            raise AssertionError("Fake transport has no queued outcome.")

        outcome = self._outcomes.pop(0)

        if isinstance(
            outcome,
            Exception,
        ):
            raise outcome

        return outcome


def make_evidence() -> list[ProviderEvidence]:
    """Build deterministic teacher evidence."""

    return [
        ProviderEvidence(
            evidence_id="E1",
            text=(
                "The thermal-management "
                "architecture uses a liquid "
                "cooling loop to transport "
                "waste heat from electrical "
                "components."
            ),
        ),
        ProviderEvidence(
            evidence_id="E2",
            text=("A radiator rejects the transported heat to the surrounding airflow."),
        ),
        ProviderEvidence(
            evidence_id="E3",
            text=("Pump power and radiator size contribute to the aircraft-level trade space."),
        ),
    ]


def make_question_config() -> TeacherQuestionConfig:
    """Build deterministic question-validation settings."""

    return TeacherQuestionConfig(
        timeout_seconds=30.0,
        max_retries=2,
        retry_backoff_seconds=1.0,
        max_draft_attempts=3,
        minimum_characters=25,
        maximum_characters=320,
    )


def test_structured_teacher_parses_question_and_usage() -> None:
    transport = QueueTransport(
        [
            StructuredModelResult(
                payload={
                    "question": (
                        "How does the thermal-management "
                        "architecture transport and reject "
                        "waste heat?"
                    )
                },
                request_id="req_test_001",
                usage=ProviderUsage(
                    input_tokens=100,
                    output_tokens=20,
                ),
            )
        ]
    )

    client = StructuredTeacherClient(
        model_name="teacher-test",
        transport=transport,
        timeout_seconds=30.0,
        max_retries=0,
        retry_backoff_seconds=0.0,
        input_cost_per_million_tokens=1.0,
        output_cost_per_million_tokens=5.0,
        clock=lambda: 10.0,
    )

    result, telemetry = client.complete(
        prompt=(build_ordinary_question_prompt(make_evidence()[:2])),
        response_model=(TeacherQuestionDraft),
    )

    assert result.question == (
        "How does the thermal-management architecture transport and reject waste heat?"
    )

    assert telemetry.request_id == "req_test_001"

    assert telemetry.usage is not None

    assert telemetry.usage.total_tokens == 120

    assert telemetry.estimated_cost_usd == pytest.approx(0.0002)


def test_structured_teacher_retries_retryable_transport_error() -> None:
    transport = QueueTransport(
        [
            ProviderTransportError(
                "temporary failure",
                retryable=True,
            ),
            StructuredModelResult(
                payload={"question": ("How is waste heat rejected from the system?")},
            ),
        ]
    )

    sleeps: list[float] = []

    client = StructuredTeacherClient(
        model_name="teacher-test",
        transport=transport,
        timeout_seconds=30.0,
        max_retries=1,
        retry_backoff_seconds=0.5,
        sleep=sleeps.append,
    )

    result, telemetry = client.complete(
        prompt=(build_ordinary_question_prompt(make_evidence()[:2])),
        response_model=(TeacherQuestionDraft),
    )

    assert result.question == ("How is waste heat rejected from the system?")

    assert telemetry.attempts == 2

    assert sleeps == [0.5]


def test_question_prompts_do_not_contain_source_ids() -> None:
    evidence = make_evidence()

    ordinary = build_ordinary_question_prompt(evidence[:2])

    synthesis = build_synthesis_question_prompt(evidence)

    refusal = build_refusal_question_prompt(evidence[:2])

    combined = " ".join(
        [
            ordinary.user_prompt,
            synthesis.user_prompt,
            refusal.user_prompt,
        ]
    )

    assert ":chunk:" not in combined

    assert "20160009765" not in combined


def test_valid_question_is_normalized() -> None:
    question = "  How   does the cooling loop transport waste heat to the radiator?  "

    normalized = validate_teacher_question(
        question,
        document_id=20160009765,
        config=(make_question_config()),
    )

    assert normalized == ("How does the cooling loop transport waste heat to the radiator?")


@pytest.mark.parametrize(
    "question",
    [
        ("According to E1, how does the cooling loop operate?"),
        ("What information appears in 20160009765:chunk:00001?"),
        ("What does document 20160009765 report about cooling?"),
        ("Based on the provided evidence, how is waste heat rejected?"),
    ],
)
def test_invalid_question_meta_language_is_rejected(
    question: str,
) -> None:
    with pytest.raises(TeacherQuestionValidationError):
        validate_teacher_question(
            question,
            document_id=20160009765,
            config=(make_question_config()),
        )


def test_question_without_question_mark_is_rejected() -> None:
    with pytest.raises(
        TeacherQuestionValidationError,
        match="question mark",
    ):
        validate_teacher_question(
            ("Explain how the cooling loop transports waste heat"),
            document_id=20160009765,
            config=(make_question_config()),
        )


def test_refusal_assessment_requires_missing_information() -> None:
    with pytest.raises(
        ValueError,
        match="missing information",
    ):
        RefusalSupportAssessment(
            supported_by_evidence=False,
            missing_information=None,
        )


def test_refusal_assessment_accepts_unsupported_result() -> None:
    assessment = RefusalSupportAssessment(
        supported_by_evidence=False,
        missing_information=("The excerpts do not state a certification temperature limit."),
    )

    assert assessment.supported_by_evidence is False

    assert assessment.missing_information is not None


def test_refusal_verification_prompt_contains_question() -> None:
    question = "What exact certification temperature limit applies?"

    prompt = build_refusal_verification_prompt(
        question=question,
        evidence=(make_evidence()[:2]),
    )

    assert question in (prompt.user_prompt)

    assert "supported_by_evidence" in prompt.user_prompt
