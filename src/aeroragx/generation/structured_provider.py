"""Structured generation provider with retries and telemetry."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Protocol, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from aeroragx.generation.guardrails import (
    PromptInjectionAssessment,
    enforce_prompt_injection_policy,
)
from aeroragx.generation.prompting import (
    ProviderHardeningConfig,
    build_grounded_prompt,
)
from aeroragx.generation.provider import (
    GenerationProvider,
    ProviderEvidence,
    ProviderResponse,
)


class ProviderUsage(BaseModel):
    """Provider-reported token usage."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)

    @property
    def total_tokens(self) -> int | None:
        """Return total usage when both components are available."""

        if self.input_tokens is None or self.output_tokens is None:
            return None

        return self.input_tokens + self.output_tokens


class ProviderTelemetry(BaseModel):
    """Auditable metadata for one structured provider call."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    attempts: int = Field(ge=1)
    latency_seconds: float = Field(ge=0.0)
    succeeded: bool
    request_id: str | None = None
    usage: ProviderUsage | None = None
    estimated_cost_usd: float | None = Field(
        default=None,
        ge=0.0,
    )
    prompt_injection_safe: bool
    prompt_injection_findings: int = Field(ge=0)
    error_type: str | None = None


class StructuredModelRequest(BaseModel):
    """Provider-neutral request created from one grounded prompt."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    response_schema: dict[str, object]


class StructuredModelResult(BaseModel):
    """Provider-neutral structured model result."""

    model_config = ConfigDict(extra="forbid")

    payload: dict[str, object]
    request_id: str | None = None
    usage: ProviderUsage | None = None


class StructuredModelTransport(Protocol):
    """Transport implemented by a concrete local or remote model backend."""

    def complete(
        self,
        *,
        request: StructuredModelRequest,
        timeout_seconds: float,
    ) -> StructuredModelResult:
        """Execute one structured model request."""

        ...


class StructuredProviderError(RuntimeError):
    """Base error raised by the structured provider layer."""


class ProviderTransportError(StructuredProviderError):
    """Transport failure that may optionally be retried."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        diagnostics: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.diagnostics = dict(diagnostics or {})


class ProviderResponseValidationError(StructuredProviderError):
    """Model output failed the required response contract."""

    def __init__(self, message: str, *, diagnostics: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = dict(diagnostics or {})


class StructuredGenerationProvider(GenerationProvider):
    """Generation provider with prompt hardening, retries, and telemetry."""

    def __init__(
        self,
        *,
        model_name: str,
        transport: StructuredModelTransport,
        config: ProviderHardeningConfig,
        input_cost_per_million_tokens: float = 0.0,
        output_cost_per_million_tokens: float = 0.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        normalized_model_name = model_name.strip()

        if not normalized_model_name:
            raise ValueError("model_name must not be blank.")

        if input_cost_per_million_tokens < 0.0:
            raise ValueError("input_cost_per_million_tokens must be non-negative.")

        if output_cost_per_million_tokens < 0.0:
            raise ValueError("output_cost_per_million_tokens must be non-negative.")

        self._model_name = normalized_model_name
        self._transport = transport
        self._config = config
        self._input_cost_per_million_tokens = input_cost_per_million_tokens
        self._output_cost_per_million_tokens = output_cost_per_million_tokens
        self._sleep = sleep
        self._clock = clock
        self._last_telemetry: ProviderTelemetry | None = None

    @property
    def last_telemetry(self) -> ProviderTelemetry | None:
        """Return telemetry from the latest attempted generation call."""

        if self._last_telemetry is None:
            return None

        return self._last_telemetry.model_copy(deep=True)

    def count_tokens(self, text: str) -> int:
        """Delegate exact token counting when the concrete transport supports it."""

        counter = getattr(self._transport, "count_tokens", None)
        if not callable(counter):
            raise NotImplementedError("This model transport does not expose token counting.")
        value = counter(text)
        if not isinstance(value, int) or value < 0:
            raise ValueError("Transport token counter returned an invalid value.")
        return value

    @property
    def supports_token_count(self) -> bool:
        """Return whether this provider can count with its runtime tokenizer."""

        return callable(getattr(self._transport, "count_tokens", None))

    def generate(
        self,
        *,
        query: str,
        evidence: Sequence[ProviderEvidence],
        max_claims: int,
    ) -> ProviderResponse:
        """Generate and validate one grounded structured response."""

        copied_evidence = [item.model_copy(deep=True) for item in evidence]

        injection = enforce_prompt_injection_policy(
            evidence=copied_evidence,
            config=self._config,
        )

        prompt = build_grounded_prompt(
            query=query,
            evidence=copied_evidence,
            max_claims=max_claims,
            config=self._config,
        )

        request = StructuredModelRequest(
            model_name=self._model_name,
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            response_schema=cast(
                dict[str, object],
                ProviderResponse.model_json_schema(),
            ),
        )

        started_at = self._clock()
        attempts = 0
        maximum_attempts = self._config.max_retries + 1

        while attempts < maximum_attempts:
            attempts += 1

            try:
                result = self._transport.complete(
                    request=request,
                    timeout_seconds=(self._config.timeout_seconds),
                )
            except ProviderTransportError as error:
                if not error.retryable or attempts >= maximum_attempts:
                    self._record_failure(
                        started_at=started_at,
                        attempts=attempts,
                        injection=injection,
                        error_type=(type(error).__name__),
                    )
                    raise

                self._sleep(self._retry_delay_seconds(attempts))
                continue

            try:
                response = ProviderResponse.model_validate(result.payload)
                response = self._normalize_duplicate_evidence_ids(
                    response=response,
                )
                self._validate_response_evidence_ids(
                    response=response,
                    supplied_evidence=(copied_evidence),
                )
            except (
                ValidationError,
                ValueError,
            ) as error:
                self._record_failure(
                    started_at=started_at,
                    attempts=attempts,
                    injection=injection,
                    error_type=("ProviderResponseValidationError"),
                    request_id=result.request_id,
                    usage=result.usage,
                )
                raise ProviderResponseValidationError(
                    "Structured provider response failed validation.",
                    diagnostics={
                        "failure_stage": "response_schema",
                        "validation_error_type": type(error).__name__,
                    },
                ) from error

            self._last_telemetry = ProviderTelemetry(
                model_name=self._model_name,
                prompt_version=(self._config.prompt_version),
                attempts=attempts,
                latency_seconds=max(
                    0.0,
                    self._clock() - started_at,
                ),
                succeeded=True,
                request_id=result.request_id,
                usage=result.usage,
                estimated_cost_usd=(self._estimate_cost(result.usage)),
                prompt_injection_safe=(injection.safe),
                prompt_injection_findings=len(injection.findings),
                error_type=None,
            )

            return response

        raise AssertionError("Structured provider retry loop exited unexpectedly.")

    def _retry_delay_seconds(
        self,
        completed_attempts: int,
    ) -> float:
        """Return deterministic linear retry backoff."""

        return self._config.retry_backoff_seconds * completed_attempts

    def _estimate_cost(
        self,
        usage: ProviderUsage | None,
    ) -> float | None:
        """Estimate request cost from configured token prices."""

        if usage is None or usage.input_tokens is None or usage.output_tokens is None:
            return None

        input_cost = usage.input_tokens / 1_000_000 * self._input_cost_per_million_tokens
        output_cost = usage.output_tokens / 1_000_000 * self._output_cost_per_million_tokens

        return input_cost + output_cost

    def _record_failure(
        self,
        *,
        started_at: float,
        attempts: int,
        injection: PromptInjectionAssessment,
        error_type: str,
        request_id: str | None = None,
        usage: ProviderUsage | None = None,
    ) -> None:
        """Record telemetry for one failed provider call."""

        self._last_telemetry = ProviderTelemetry(
            model_name=self._model_name,
            prompt_version=(self._config.prompt_version),
            attempts=attempts,
            latency_seconds=max(
                0.0,
                self._clock() - started_at,
            ),
            succeeded=False,
            request_id=request_id,
            usage=usage,
            estimated_cost_usd=(self._estimate_cost(usage)),
            prompt_injection_safe=(injection.safe),
            prompt_injection_findings=len(injection.findings),
            error_type=error_type,
        )

    @staticmethod
    def _normalize_duplicate_evidence_ids(
        *,
        response: ProviderResponse,
    ) -> ProviderResponse:
        """Deduplicate claim evidence IDs while preserving their order."""

        normalized_claims = [
            claim.model_copy(
                update={"evidence_ids": list(dict.fromkeys(claim.evidence_ids))},
                deep=True,
            )
            for claim in response.claims
        ]

        return response.model_copy(
            update={
                "claims": normalized_claims,
            },
            deep=True,
        )

    @staticmethod
    def _validate_response_evidence_ids(
        *,
        response: ProviderResponse,
        supplied_evidence: Sequence[ProviderEvidence],
    ) -> None:
        """Reject evidence references not supplied to the provider."""

        valid_ids = {item.evidence_id for item in supplied_evidence}

        unknown_ids = sorted(
            {
                evidence_id
                for claim in response.claims
                for evidence_id in claim.evidence_ids
                if evidence_id not in valid_ids
            }
        )

        if unknown_ids:
            raise ValueError(
                "Provider response referenced unknown evidence IDs: " + ", ".join(unknown_ids)
            )
