"""Structured teacher utilities for LoRA dataset construction."""

from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar, cast

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

from aeroragx.generation.http_transport import (
    HttpStructuredModelTransport,
    load_http_transport_config,
)
from aeroragx.generation.model_adapter import (
    OpenAIResponsesAdapter,
)
from aeroragx.generation.provider import (
    ProviderEvidence,
)
from aeroragx.generation.provider_factory import (
    load_provider_runtime_config,
)
from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelTransport,
)

ModelT = TypeVar(
    "ModelT",
    bound=BaseModel,
)


class TeacherProviderConfig(BaseModel):
    """Paths and schema metadata for the remote teacher."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    generation_config: str = Field(
        min_length=1,
    )

    provider_config: str = Field(
        min_length=1,
    )

    http_transport_config: str = Field(
        min_length=1,
    )

    provider_runtime_config: str = Field(
        min_length=1,
    )

    teacher_schema_name: str = Field(
        min_length=1,
    )


class TeacherQuestionConfig(BaseModel):
    """Controls for teacher-authored question generation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    timeout_seconds: float = Field(
        gt=0.0,
    )

    max_retries: int = Field(
        ge=0,
        le=10,
    )

    retry_backoff_seconds: float = Field(
        ge=0.0,
    )

    max_draft_attempts: int = Field(
        ge=1,
        le=10,
    )

    minimum_characters: int = Field(
        ge=1,
    )

    maximum_characters: int = Field(
        ge=1,
    )

    @model_validator(mode="after")
    def validate_question_limits(
        self,
    ) -> TeacherQuestionConfig:
        """Ensure question-length limits are ordered."""

        if self.minimum_characters > self.maximum_characters:
            raise ValueError("minimum_characters must not exceed maximum_characters.")

        return self


class TeacherSupportedConfig(BaseModel):
    """Claim limits for supported training examples."""

    model_config = ConfigDict(
        extra="forbid",
    )

    max_claims: int = Field(
        ge=1,
        le=100,
    )


class TeacherRefusalConfig(BaseModel):
    """Controls for refusal-example generation."""

    model_config = ConfigDict(
        extra="forbid",
    )

    validation_enabled: bool = True


class TeacherConfig(BaseModel):
    """Complete teacher configuration for dataset construction."""

    model_config = ConfigDict(
        extra="forbid",
    )

    version: str = Field(
        min_length=1,
    )

    provider: TeacherProviderConfig

    question_generation: TeacherQuestionConfig

    ordinary: TeacherSupportedConfig

    synthesis: TeacherSupportedConfig

    refusal: TeacherRefusalConfig


class TeacherQuestionDraft(BaseModel):
    """One teacher-authored natural technical question."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        min_length=1,
    )


class RefusalSupportAssessment(BaseModel):
    """Determine whether a proposed refusal question is answerable."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    supported_by_evidence: bool

    missing_information: str | None = None

    @model_validator(mode="after")
    def validate_missing_information(
        self,
    ) -> RefusalSupportAssessment:
        """Require a missing-information description for unsupported questions."""

        if not self.supported_by_evidence and (
            self.missing_information is None or not self.missing_information.strip()
        ):
            raise ValueError("Unsupported refusal questions must identify the missing information.")

        return self


class TeacherPrompt(BaseModel):
    """Provider-neutral teacher prompt."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    system_prompt: str = Field(
        min_length=1,
    )

    user_prompt: str = Field(
        min_length=1,
    )


class TeacherCallTelemetry(BaseModel):
    """Telemetry for one teacher structured-output call."""

    model_config = ConfigDict(
        extra="forbid",
    )

    model_name: str = Field(
        min_length=1,
    )

    attempts: int = Field(
        ge=1,
    )

    latency_seconds: float = Field(
        ge=0.0,
    )

    request_id: str | None = None

    usage: ProviderUsage | None = None

    estimated_cost_usd: float | None = Field(
        default=None,
        ge=0.0,
    )


class TeacherError(RuntimeError):
    """Base error raised by training-teacher infrastructure."""


class TeacherResponseValidationError(TeacherError):
    """Teacher output failed its requested structured schema."""


class TeacherQuestionValidationError(TeacherError):
    """Teacher-authored question failed deterministic validation."""


class StructuredTeacherClient:
    """Generic structured-output client for teacher-only schemas."""

    def __init__(
        self,
        *,
        model_name: str,
        transport: StructuredModelTransport,
        timeout_seconds: float,
        max_retries: int,
        retry_backoff_seconds: float,
        input_cost_per_million_tokens: float = 0.0,
        output_cost_per_million_tokens: float = 0.0,
        sleep: Callable[
            [float],
            None,
        ] = time.sleep,
        clock: Callable[
            [],
            float,
        ] = time.perf_counter,
    ) -> None:
        normalized_model_name = model_name.strip()

        if not normalized_model_name:
            raise ValueError("model_name must not be blank.")

        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive.")

        if max_retries < 0:
            raise ValueError("max_retries must be non-negative.")

        if retry_backoff_seconds < 0.0:
            raise ValueError("retry_backoff_seconds must be non-negative.")

        if input_cost_per_million_tokens < 0.0:
            raise ValueError("input token cost must be non-negative.")

        if output_cost_per_million_tokens < 0.0:
            raise ValueError("output token cost must be non-negative.")

        self._model_name = normalized_model_name

        self._transport = transport

        self._timeout_seconds = timeout_seconds

        self._max_retries = max_retries

        self._retry_backoff_seconds = retry_backoff_seconds

        self._input_cost_per_million_tokens = input_cost_per_million_tokens

        self._output_cost_per_million_tokens = output_cost_per_million_tokens

        self._sleep = sleep

        self._clock = clock

    @property
    def model_name(
        self,
    ) -> str:
        """Return the configured teacher model."""

        return self._model_name

    def complete(
        self,
        *,
        prompt: TeacherPrompt,
        response_model: type[ModelT],
    ) -> tuple[
        ModelT,
        TeacherCallTelemetry,
    ]:
        """Execute one structured teacher request."""

        schema = cast(
            dict[str, object],
            response_model.model_json_schema(),
        )

        request = StructuredModelRequest(
            model_name=(self._model_name),
            system_prompt=(prompt.system_prompt),
            user_prompt=(prompt.user_prompt),
            response_schema=(schema),
        )

        started_at = self._clock()

        attempts = 0

        maximum_attempts = self._max_retries + 1

        while attempts < maximum_attempts:
            attempts += 1

            try:
                result = self._transport.complete(
                    request=request,
                    timeout_seconds=(self._timeout_seconds),
                )

            except ProviderTransportError as error:
                if not error.retryable or attempts >= maximum_attempts:
                    raise

                self._sleep(self._retry_backoff_seconds * attempts)

                continue

            try:
                parsed = response_model.model_validate(result.payload)

            except ValidationError as error:
                raise (
                    TeacherResponseValidationError(
                        "Teacher structured response failed schema validation."
                    )
                ) from error

            telemetry = TeacherCallTelemetry(
                model_name=(self._model_name),
                attempts=attempts,
                latency_seconds=max(
                    0.0,
                    self._clock() - started_at,
                ),
                request_id=(result.request_id),
                usage=result.usage,
                estimated_cost_usd=(self._estimate_cost(result.usage)),
            )

            return (
                parsed,
                telemetry,
            )

        raise AssertionError("Teacher retry loop exited unexpectedly.")

    def _estimate_cost(
        self,
        usage: ProviderUsage | None,
    ) -> float | None:
        """Estimate external API cost from token usage."""

        if usage is None or usage.input_tokens is None or usage.output_tokens is None:
            return None

        input_cost = usage.input_tokens / 1_000_000 * self._input_cost_per_million_tokens

        output_cost = usage.output_tokens / 1_000_000 * self._output_cost_per_million_tokens

        return input_cost + output_cost


def load_teacher_config(
    path: Path,
) -> TeacherConfig:
    """Load and validate teacher YAML configuration."""

    raw_value = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(
        raw_value,
        dict,
    ):
        raise ValueError("Teacher configuration must contain a YAML mapping.")

    return TeacherConfig.model_validate(raw_value)


def create_openai_teacher_client(
    config: TeacherConfig,
    *,
    environment: (dict[str, str] | None) = None,
) -> StructuredTeacherClient:
    """Create the existing HTTP/OpenAI stack for teacher-only schemas."""

    runtime_config_path = Path(config.provider.provider_runtime_config)

    http_config_path = Path(config.provider.http_transport_config)

    runtime_config = load_provider_runtime_config(runtime_config_path)

    http_config = load_http_transport_config(http_config_path)

    if runtime_config.adapter != "openai-responses":
        raise ValueError("Teacher provider requires adapter='openai-responses'.")

    adapter = OpenAIResponsesAdapter(schema_name=(config.provider.teacher_schema_name))

    transport = HttpStructuredModelTransport(
        config=http_config,
        adapter=adapter,
        environment=environment,
    )

    return StructuredTeacherClient(
        model_name=(runtime_config.priced_model_name),
        transport=transport,
        timeout_seconds=(config.question_generation.timeout_seconds),
        max_retries=(config.question_generation.max_retries),
        retry_backoff_seconds=(config.question_generation.retry_backoff_seconds),
        input_cost_per_million_tokens=(runtime_config.input_cost_per_million_tokens),
        output_cost_per_million_tokens=(runtime_config.output_cost_per_million_tokens),
    )


def build_ordinary_question_prompt(
    evidence: Sequence[ProviderEvidence],
) -> TeacherPrompt:
    """Build a prompt for one evidence-grounded ordinary question."""

    return TeacherPrompt(
        system_prompt=(
            "You create one natural technical "
            "engineering question for supervised "
            "training data. The question must be "
            "answerable solely from the supplied "
            "technical excerpts. Do not answer the "
            "question. Do not mention evidence IDs, "
            "chunks, documents, prompts, or the "
            "training-data process."
        ),
        user_prompt=(
            "Create one specific engineering "
            "question that requires information "
            "contained in these excerpts.\n\n"
            "Requirements:\n"
            "- It must be answerable from the excerpts.\n"
            "- It should depend on technical details, "
            "not generic common knowledge.\n"
            "- It should sound like a natural user question.\n"
            "- Do not mention E1, E2, evidence, chunks, "
            "or document identifiers.\n"
            "- Return only the structured question field.\n\n" + _render_evidence(evidence)
        ),
    )


def build_synthesis_question_prompt(
    evidence: Sequence[ProviderEvidence],
) -> TeacherPrompt:
    """Build a prompt requiring multi-evidence technical synthesis."""

    return TeacherPrompt(
        system_prompt=(
            "You create exactly one natural technical engineering "
            "question for supervised training data. The question "
            "must require synthesis across multiple supplied technical "
            "passages. Do not answer the question. The final question "
            "must sound like something an engineer would naturally ask."
        ),
        user_prompt=(
            "Create exactly one coherent engineering question whose "
            "complete answer requires material information from at "
            "least two of the technical passages below.\n\n"
            "STRICT OUTPUT REQUIREMENTS:\n"
            "- Return one question only in the structured question field.\n"
            "- The question must be one sentence.\n"
            "- The question must end with a question mark.\n"
            "- Keep the question under 240 characters.\n"
            "- The question must be answerable from the technical content.\n"
            "- It should require several materially distinct technical "
            "facts or relationships.\n"
            "- Do not mention E1, E2, E3, or any evidence identifier.\n"
            "- Do not use the words evidence, excerpt, excerpts, supplied, "
            "provided, document, documents, chunk, chunks, prompt, "
            "training, or dataset in the question.\n"
            "- Do not include document numbers or source identifiers.\n"
            "- Do not include the answer.\n\n"
            "Technical passages:\n\n" + _render_evidence(evidence)
        ),
    )


def build_refusal_question_prompt(
    evidence: Sequence[ProviderEvidence],
) -> TeacherPrompt:
    """Build a near-domain question intentionally unsupported by evidence."""

    return TeacherPrompt(
        system_prompt=(
            "You create one difficult negative "
            "training question. The question must "
            "be closely related to the technical "
            "domain of the supplied excerpts, but "
            "the specific fact requested must NOT "
            "be established by those excerpts. "
            "Do not answer the question."
        ),
        user_prompt=(
            "Create one natural engineering question "
            "that looks relevant to these excerpts "
            "but asks for a specific fact, quantity, "
            "threshold, criterion, result, or design "
            "detail that cannot be determined from "
            "the excerpts alone.\n\n"
            "Requirements:\n"
            "- Keep the question technically plausible.\n"
            "- Keep it closely related to the excerpt domain.\n"
            "- The requested information must be absent.\n"
            "- Do not ask an absurd or unrelated question.\n"
            "- Do not mention evidence, E1, E2, chunks, "
            "documents, or the training process.\n"
            "- Return only the structured question field.\n\n" + _render_evidence(evidence)
        ),
    )


def build_refusal_verification_prompt(
    *,
    question: str,
    evidence: Sequence[ProviderEvidence],
) -> TeacherPrompt:
    """Ask the teacher to verify that a refusal question is unsupported."""

    return TeacherPrompt(
        system_prompt=(
            "You verify whether a technical question "
            "can be answered solely from supplied "
            "excerpts. Judge only information explicitly "
            "supported by those excerpts. Do not infer "
            "missing numerical values, certification "
            "requirements, operating limits, or results."
        ),
        user_prompt=(
            "Question:\n"
            f"{question}\n\n"
            "Determine whether this question can be "
            "answered reliably from the excerpts below.\n\n"
            "If it can be answered, set "
            "supported_by_evidence=true.\n"
            "If it cannot be answered, set "
            "supported_by_evidence=false and briefly "
            "identify the specific missing information.\n\n" + _render_evidence(evidence)
        ),
    )


def validate_teacher_question(
    question: str,
    *,
    document_id: int,
    config: TeacherQuestionConfig,
) -> str:
    """Normalize and deterministically validate a teacher-authored question."""

    normalized = " ".join(question.split())

    if len(normalized) < config.minimum_characters:
        raise (
            TeacherQuestionValidationError(
                "Teacher question is shorter than the configured minimum."
            )
        )

    if len(normalized) > config.maximum_characters:
        raise (
            TeacherQuestionValidationError(
                "Teacher question is longer than the configured maximum."
            )
        )

    if not normalized.endswith("?"):
        raise (TeacherQuestionValidationError("Teacher question must end with a question mark."))

    if re.search(
        r"\bE\d+\b",
        normalized,
        flags=re.IGNORECASE,
    ):
        raise (TeacherQuestionValidationError("Teacher question must not reference evidence IDs."))

    if re.search(
        r":chunk:",
        normalized,
        flags=re.IGNORECASE,
    ):
        raise (TeacherQuestionValidationError("Teacher question must not contain raw chunk IDs."))

    if str(document_id) in normalized:
        raise (
            TeacherQuestionValidationError("Teacher question must not contain the raw document ID.")
        )

    forbidden_phrases = (
        "provided evidence",
        "supplied evidence",
        "according to the evidence",
        "based on the evidence",
        "provided excerpts",
        "supplied excerpts",
        "according to the excerpts",
        "based on the excerpts",
        "training data",
        "training example",
    )

    folded = normalized.casefold()

    for phrase in forbidden_phrases:
        if phrase in folded:
            raise (
                TeacherQuestionValidationError(
                    f"Teacher question contains forbidden meta-language: {phrase!r}."
                )
            )

    return normalized


def _render_evidence(
    evidence: Sequence[ProviderEvidence],
) -> str:
    """Render provider evidence without exposing source identifiers."""

    if not evidence:
        raise ValueError("Teacher evidence must not be empty.")

    evidence_ids = [item.evidence_id for item in evidence]

    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Teacher evidence IDs must be unique.")

    sections: list[str] = []

    for item in evidence:
        sections.append(f"{item.evidence_id}:\n{item.text}")

    return "\n\n".join(sections)
