"""Build validated LoRA training examples from frozen evidence plans."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from aeroragx.generation.provider import (
    GenerationProvider,
    ProviderEvidence,
    ProviderResponse,
)
from aeroragx.generation.structured_provider import (
    ProviderTelemetry,
    StructuredGenerationProvider,
)
from aeroragx.processing.chunking import ChunkRecord
from aeroragx.training.dataset import (
    TrainingEvidence,
    TrainingExample,
)
from aeroragx.training.planning import (
    ExamplePlanType,
    PlannedExample,
)
from aeroragx.training.teacher import (
    RefusalSupportAssessment,
    StructuredTeacherClient,
    TeacherCallTelemetry,
    TeacherConfig,
    TeacherQuestionDraft,
    TeacherQuestionValidationError,
    build_ordinary_question_prompt,
    build_refusal_question_prompt,
    build_refusal_verification_prompt,
    build_synthesis_question_prompt,
    validate_teacher_question,
)

REFUSAL_TARGET_ANSWER = "The supplied evidence is insufficient to answer this question reliably."


class ExampleBuildError(RuntimeError):
    """A frozen example plan could not produce a valid training example."""


class ResolvedPlanEvidence(BaseModel):
    """Exact frozen evidence resolved for one example plan."""

    model_config = ConfigDict(
        extra="forbid",
    )

    plan_id: str = Field(
        min_length=1,
    )

    example_type: ExamplePlanType

    document_id: int = Field(
        ge=1,
    )

    training_evidence: list[TrainingEvidence] = Field(
        min_length=1,
    )

    provider_evidence: list[ProviderEvidence] = Field(
        min_length=1,
    )


class ExampleBuildResult(BaseModel):
    """Successfully generated and validated training example."""

    model_config = ConfigDict(
        extra="forbid",
    )

    plan_id: str = Field(
        min_length=1,
    )

    example_type: ExamplePlanType

    question_attempts: int = Field(
        ge=1,
    )

    question_telemetry: list[TeacherCallTelemetry] = Field(
        min_length=1,
    )

    verification_telemetry: list[TeacherCallTelemetry] = Field(
        default_factory=list,
    )

    answer_telemetry: list[ProviderTelemetry] = Field(
        default_factory=list,
    )

    example: TrainingExample


class TrainingExampleBuilder:
    """Turn frozen evidence plans into validated supervised examples."""

    def __init__(
        self,
        *,
        chunks: Sequence[ChunkRecord],
        selected_document_ids: Collection[int],
        protected_document_ids: Collection[int],
        teacher_config: TeacherConfig,
        question_client: StructuredTeacherClient,
        answer_provider: GenerationProvider,
    ) -> None:
        self._selected_document_ids = set(selected_document_ids)

        self._protected_document_ids = set(protected_document_ids)

        if not self._selected_document_ids:
            raise ValueError("selected_document_ids must not be empty.")

        overlap = self._selected_document_ids & self._protected_document_ids

        if overlap:
            raise ValueError(
                "Selected training documents overlap "
                "the protected evaluation set: "
                + ", ".join(str(document_id) for document_id in sorted(overlap))
            )

        self._chunks_by_id: dict[
            str,
            ChunkRecord,
        ] = {}

        for chunk in chunks:
            if chunk.chunk_id in self._chunks_by_id:
                raise ValueError(
                    f"Processed corpus contains duplicate chunk ID {chunk.chunk_id!r}."
                )

            self._chunks_by_id[chunk.chunk_id] = chunk

        self._teacher_config = teacher_config

        self._question_client = question_client

        self._answer_provider = answer_provider

    def build(
        self,
        plan: PlannedExample,
    ) -> ExampleBuildResult:
        """Build one training example from one frozen plan."""

        resolved = self.resolve_plan_evidence(plan)

        if plan.example_type == "refusal":
            return self._build_refusal_example(
                plan=plan,
                resolved=resolved,
            )

        return self._build_supported_example(
            plan=plan,
            resolved=resolved,
        )

    def resolve_plan_evidence(
        self,
        plan: PlannedExample,
    ) -> ResolvedPlanEvidence:
        """Resolve exact frozen chunk IDs into E1/E2/E3 evidence."""

        if plan.document_id not in self._selected_document_ids:
            raise ExampleBuildError(
                f"{plan.plan_id}: source document "
                f"{plan.document_id} is not part "
                "of the frozen LoRA source selection."
            )

        if plan.document_id in self._protected_document_ids:
            raise ExampleBuildError(
                f"{plan.plan_id}: source document {plan.document_id} is protected."
            )

        resolved_chunks: list[ChunkRecord] = []

        for chunk_id in plan.chunk_ids:
            chunk = self._chunks_by_id.get(chunk_id)

            if chunk is None:
                raise ExampleBuildError(
                    f"{plan.plan_id}: planned "
                    f"chunk {chunk_id!r} "
                    "does not exist in the "
                    "processed corpus."
                )

            if chunk.document_id != plan.document_id:
                raise ExampleBuildError(
                    f"{plan.plan_id}: chunk "
                    f"{chunk_id!r} belongs to "
                    f"document {chunk.document_id}, "
                    "but the frozen plan expects "
                    f"document {plan.document_id}."
                )

            resolved_chunks.append(chunk)

        training_evidence = [
            TrainingEvidence(
                evidence_id=(f"E{index}"),
                text=chunk.text,
                document_id=(chunk.document_id),
                chunk_id=(chunk.chunk_id),
            )
            for index, chunk in enumerate(
                resolved_chunks,
                start=1,
            )
        ]

        provider_evidence = [
            ProviderEvidence(
                evidence_id=(evidence.evidence_id),
                text=evidence.text,
            )
            for evidence in training_evidence
        ]

        return ResolvedPlanEvidence(
            plan_id=(plan.plan_id),
            example_type=(plan.example_type),
            document_id=(plan.document_id),
            training_evidence=(training_evidence),
            provider_evidence=(provider_evidence),
        )

    def _build_supported_example(
        self,
        *,
        plan: PlannedExample,
        resolved: ResolvedPlanEvidence,
    ) -> ExampleBuildResult:
        """Build ordinary or synthesis training supervision."""

        if plan.example_type == "ordinary":
            max_claims = self._teacher_config.ordinary.max_claims

            maximum_response_attempts = 1

        elif plan.example_type == "synthesis":
            max_claims = self._teacher_config.synthesis.max_claims

            maximum_response_attempts = self._teacher_config.question_generation.max_draft_attempts

        else:
            raise AssertionError("Supported builder received a non-supported example type.")

        question_telemetry: list[TeacherCallTelemetry] = []

        answer_telemetry: list[ProviderTelemetry] = []

        repair_context: str | None = None

        last_response_error: str | None = None

        for _ in range(maximum_response_attempts):
            (
                question,
                current_question_telemetry,
            ) = self._draft_supported_question(
                plan=plan,
                evidence=(resolved.provider_evidence),
                repair_context=(repair_context),
            )

            question_telemetry.extend(current_question_telemetry)

            response = self._answer_provider.generate(
                query=question,
                evidence=(resolved.provider_evidence),
                max_claims=max_claims,
            )

            current_answer_telemetry = self._answer_telemetry()

            if current_answer_telemetry is not None:
                answer_telemetry.append(current_answer_telemetry)

            if response.insufficient_evidence:
                error_message = (
                    f"{plan.plan_id}: supported "
                    "teacher answer unexpectedly "
                    "reported insufficient evidence."
                )

                if plan.example_type == "ordinary":
                    raise ExampleBuildError(error_message)

                last_response_error = error_message

                repair_context = (
                    "The previous synthesis question "
                    "produced an insufficient-evidence "
                    "answer. Draft a substantially "
                    "different question whose complete "
                    "answer requires material facts from "
                    "at least two separate technical "
                    "passages. Previous question: " + repr(question)
                )

                continue

            if plan.example_type == "synthesis":
                try:
                    self._validate_synthesis_response(
                        plan=plan,
                        response=response,
                    )

                except ExampleBuildError as error:
                    last_response_error = str(error)

                    repair_context = (
                        "The previous synthesis question "
                        "did not produce a genuinely "
                        "multi-evidence answer. "
                        "The response failed because: "
                        + last_response_error
                        + " Draft a substantially "
                        "different question whose complete "
                        "answer must combine at least one "
                        "material fact or relationship from "
                        "two or more separate technical "
                        "passages. Do not ask a question "
                        "whose complete answer can be "
                        "supported by only one passage. "
                        "Previous question: " + repr(question)
                    )

                    continue

            example = self._make_training_example(
                plan=plan,
                question=question,
                max_claims=max_claims,
                evidence=(resolved.training_evidence),
                response=response,
            )

            return ExampleBuildResult(
                plan_id=plan.plan_id,
                example_type=(plan.example_type),
                question_attempts=len(question_telemetry),
                question_telemetry=(question_telemetry),
                verification_telemetry=[],
                answer_telemetry=(answer_telemetry),
                example=example,
            )

        message = (
            f"{plan.plan_id}: synthesis "
            "response repair exhausted "
            f"{maximum_response_attempts} "
            "attempts."
        )

        if last_response_error is not None:
            message += " Last response validation error: " + last_response_error

        raise ExampleBuildError(message)

    def _build_refusal_example(
        self,
        *,
        plan: PlannedExample,
        resolved: ResolvedPlanEvidence,
    ) -> ExampleBuildResult:
        """Build one verified insufficient-evidence training example."""

        (
            question,
            question_telemetry,
            verification_telemetry,
        ) = self._draft_refusal_question(
            plan=plan,
            evidence=(resolved.provider_evidence),
        )

        response = ProviderResponse(
            answer=(REFUSAL_TARGET_ANSWER),
            claims=[],
            insufficient_evidence=True,
        )

        example = self._make_training_example(
            plan=plan,
            question=question,
            max_claims=(self._teacher_config.synthesis.max_claims),
            evidence=(resolved.training_evidence),
            response=response,
        )

        return ExampleBuildResult(
            plan_id=(plan.plan_id),
            example_type=(plan.example_type),
            question_attempts=len(question_telemetry),
            question_telemetry=(question_telemetry),
            verification_telemetry=(verification_telemetry),
            answer_telemetry=[],
            example=example,
        )

    def _draft_supported_question(
        self,
        *,
        plan: PlannedExample,
        evidence: Sequence[ProviderEvidence],
        repair_context: str | None = None,
    ) -> tuple[
        str,
        list[TeacherCallTelemetry],
    ]:
        """Draft and deterministically validate a supported question."""

        telemetry: list[TeacherCallTelemetry] = []

        last_validation_error: str | None = None

        for _ in range(self._teacher_config.question_generation.max_draft_attempts):
            if plan.example_type == "ordinary":
                prompt = build_ordinary_question_prompt(evidence)

            elif plan.example_type == "synthesis":
                prompt = build_synthesis_question_prompt(evidence)

            else:
                raise AssertionError("Supported question drafting received an invalid plan type.")

            if repair_context is not None:
                prompt = prompt.model_copy(
                    update={
                        "user_prompt": (
                            prompt.user_prompt
                            + "\n\n"
                            + "SYNTHESIS REPAIR REQUIREMENT:\n"
                            + repair_context
                        )
                    }
                )

            if last_validation_error is not None:
                prompt = prompt.model_copy(
                    update={
                        "user_prompt": (
                            prompt.user_prompt
                            + "\n\n"
                            + "A previous draft was rejected "
                            + "by deterministic validation because: "
                            + last_validation_error
                            + "\n"
                            + "Return a corrected question that "
                            + "does not repeat that problem."
                        )
                    }
                )

            (
                draft,
                call_telemetry,
            ) = self._question_client.complete(
                prompt=prompt,
                response_model=(TeacherQuestionDraft),
            )

            telemetry.append(call_telemetry)

            try:
                question = validate_teacher_question(
                    draft.question,
                    document_id=(plan.document_id),
                    config=(self._teacher_config.question_generation),
                )

            except TeacherQuestionValidationError as error:
                last_validation_error = str(error)

                continue

            return (
                question,
                telemetry,
            )

        message = (
            f"{plan.plan_id}: teacher "
            "did not produce a valid "
            "supported question within "
            "the configured draft limit."
        )

        if last_validation_error is not None:
            message += " Last validation error: " + last_validation_error

        raise ExampleBuildError(message)

    def _draft_refusal_question(
        self,
        *,
        plan: PlannedExample,
        evidence: Sequence[ProviderEvidence],
    ) -> tuple[
        str,
        list[TeacherCallTelemetry],
        list[TeacherCallTelemetry],
    ]:
        """Draft and verify a near-domain unsupported question."""

        question_telemetry: list[TeacherCallTelemetry] = []

        verification_telemetry: list[TeacherCallTelemetry] = []

        for _ in range(self._teacher_config.question_generation.max_draft_attempts):
            (
                draft,
                draft_telemetry,
            ) = self._question_client.complete(
                prompt=(build_refusal_question_prompt(evidence)),
                response_model=(TeacherQuestionDraft),
            )

            question_telemetry.append(draft_telemetry)

            try:
                question = validate_teacher_question(
                    draft.question,
                    document_id=(plan.document_id),
                    config=(self._teacher_config.question_generation),
                )

            except TeacherQuestionValidationError:
                continue

            if not self._teacher_config.refusal.validation_enabled:
                return (
                    question,
                    question_telemetry,
                    verification_telemetry,
                )

            (
                assessment,
                assessment_telemetry,
            ) = self._question_client.complete(
                prompt=(
                    build_refusal_verification_prompt(
                        question=(question),
                        evidence=evidence,
                    )
                ),
                response_model=(RefusalSupportAssessment),
            )

            verification_telemetry.append(assessment_telemetry)

            if assessment.supported_by_evidence:
                continue

            return (
                question,
                question_telemetry,
                verification_telemetry,
            )

        raise ExampleBuildError(
            f"{plan.plan_id}: teacher "
            "did not produce a verified "
            "unsupported refusal question "
            "within the configured draft limit."
        )

    @staticmethod
    def _validate_synthesis_response(
        *,
        plan: PlannedExample,
        response: ProviderResponse,
    ) -> None:
        """Require materially multi-claim, multi-evidence synthesis."""

        if len(response.claims) < 2:
            raise ExampleBuildError(
                f"{plan.plan_id}: synthesis response must contain at least two claims."
            )

        cited_evidence_ids = {
            evidence_id for claim in response.claims for evidence_id in claim.evidence_ids
        }

        if len(cited_evidence_ids) < 2:
            raise ExampleBuildError(
                f"{plan.plan_id}: synthesis response must cite at least two distinct evidence IDs."
            )

    @staticmethod
    def _make_training_example(
        *,
        plan: PlannedExample,
        question: str,
        max_claims: int,
        evidence: Sequence[TrainingEvidence],
        response: ProviderResponse,
    ) -> TrainingExample:
        """Construct the canonical training schema and wrap validation errors."""

        try:
            return TrainingExample(
                example_id=("train_" + plan.plan_id),
                query=question,
                max_claims=(max_claims),
                evidence=[item.model_copy(deep=True) for item in evidence],
                response=(response.model_copy(deep=True)),
            )

        except ValidationError as error:
            raise ExampleBuildError(
                f"{plan.plan_id}: generated "
                "training example failed "
                "canonical TrainingExample "
                "validation."
            ) from error

    def _answer_telemetry(
        self,
    ) -> ProviderTelemetry | None:
        """Return telemetry when using the structured production provider."""

        if isinstance(
            self._answer_provider,
            StructuredGenerationProvider,
        ):
            return self._answer_provider.last_telemetry

        return None
