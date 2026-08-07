"""Provider-specific request/response adapters for structured models."""

from __future__ import annotations

import json
from typing import Protocol

from aeroragx.generation.structured_provider import (
    ProviderTransportError,
    ProviderUsage,
    StructuredModelRequest,
    StructuredModelResult,
)


class StructuredModelAdapter(Protocol):
    """Translate provider-neutral requests to and from one API contract."""

    def build_request_payload(
        self,
        request: StructuredModelRequest,
    ) -> dict[str, object]:
        """Build one provider-specific JSON request body."""

        ...

    def parse_response(
        self,
        data: dict[str, object],
        *,
        fallback_request_id: str | None,
    ) -> StructuredModelResult:
        """Parse one provider-specific JSON response body."""

        ...


class GenericStructuredModelAdapter:
    """Preserve the original AeroRAG-X generic HTTP JSON contract."""

    def build_request_payload(
        self,
        request: StructuredModelRequest,
    ) -> dict[str, object]:
        """Serialize one generic structured-model request."""

        return {
            "model": request.model_name,
            "system_prompt": request.system_prompt,
            "user_prompt": request.user_prompt,
            "response_schema": request.response_schema,
        }

    def parse_response(
        self,
        data: dict[str, object],
        *,
        fallback_request_id: str | None,
    ) -> StructuredModelResult:
        """Parse the generic AeroRAG-X HTTP response contract."""

        payload_value = data.get("payload")

        if not isinstance(payload_value, dict):
            raise ProviderTransportError(
                "Structured model endpoint response is missing object field 'payload'.",
                retryable=False,
            )

        request_id = _optional_string(
            data.get("request_id"),
            field_name="request_id",
        )

        if request_id is None:
            request_id = fallback_request_id

        return StructuredModelResult(
            payload=_string_key_dict(payload_value),
            request_id=request_id,
            usage=_parse_usage(data.get("usage")),
        )


class OpenAIResponsesAdapter:
    """Adapter for the OpenAI Responses API with Structured Outputs."""

    def __init__(
        self,
        *,
        schema_name: str = "aeroragx_grounded_answer",
    ) -> None:
        normalized_schema_name = schema_name.strip()

        if not normalized_schema_name:
            raise ValueError("schema_name must not be blank.")

        self._schema_name = normalized_schema_name

    @property
    def schema_name(self) -> str:
        """Return the configured Structured Outputs schema name."""

        return self._schema_name

    def build_request_payload(
        self,
        request: StructuredModelRequest,
    ) -> dict[str, object]:
        """Build one OpenAI Responses API request."""

        strict_schema = _strict_json_schema(request.response_schema)

        return {
            "model": request.model_name,
            "input": [
                {
                    "role": "system",
                    "content": request.system_prompt,
                },
                {
                    "role": "user",
                    "content": request.user_prompt,
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": self._schema_name,
                    "strict": True,
                    "schema": strict_schema,
                }
            },
        }

    def parse_response(
        self,
        data: dict[str, object],
        *,
        fallback_request_id: str | None,
    ) -> StructuredModelResult:
        """Parse one OpenAI Responses API result."""

        status = data.get("status")

        if status != "completed":
            if status == "incomplete":
                raise ProviderTransportError(
                    "OpenAI Responses API returned an incomplete response.",
                    retryable=False,
                )

            raise ProviderTransportError(
                "OpenAI Responses API did not return a completed response.",
                retryable=False,
            )

        output = data.get("output")

        if not isinstance(output, list):
            raise ProviderTransportError(
                "OpenAI Responses API response is missing output items.",
                retryable=False,
            )

        output_text: str | None = None

        for item in output:
            if not isinstance(item, dict):
                continue

            if item.get("type") != "message":
                continue

            content = item.get("content")

            if not isinstance(content, list):
                continue

            for content_item in content:
                if not isinstance(
                    content_item,
                    dict,
                ):
                    continue

                content_type = content_item.get("type")

                if content_type == "refusal":
                    raise ProviderTransportError(
                        "OpenAI model refused the request.",
                        retryable=False,
                    )

                if content_type != "output_text":
                    continue

                text_value = content_item.get("text")

                if not isinstance(
                    text_value,
                    str,
                ):
                    raise ProviderTransportError(
                        "OpenAI output_text item is missing string text.",
                        retryable=False,
                    )

                output_text = text_value
                break

            if output_text is not None:
                break

        if output_text is None:
            raise ProviderTransportError(
                "OpenAI Responses API returned no output_text content.",
                retryable=False,
            )

        try:
            parsed_payload = json.loads(output_text)
        except json.JSONDecodeError as error:
            raise ProviderTransportError(
                "OpenAI Structured Output was not valid JSON.",
                retryable=False,
            ) from error

        if not isinstance(
            parsed_payload,
            dict,
        ):
            raise ProviderTransportError(
                "OpenAI Structured Output must be a JSON object.",
                retryable=False,
            )

        response_id = _optional_string(
            data.get("id"),
            field_name="id",
        )

        if response_id is None:
            response_id = fallback_request_id

        usage = _parse_openai_usage(data.get("usage"))

        return StructuredModelResult(
            payload=_string_key_dict(parsed_payload),
            request_id=response_id,
            usage=usage,
        )


def _strict_json_schema(
    schema: dict[str, object],
) -> dict[str, object]:
    """Normalize a JSON schema for strict structured output."""

    normalized = _normalize_schema_value(schema)

    if not isinstance(normalized, dict):
        raise ValueError("response_schema must be a JSON object.")

    return _string_key_dict(normalized)


def _normalize_schema_value(
    value: object,
) -> object:
    """Recursively normalize one JSON-schema value."""

    if isinstance(value, list):
        return [_normalize_schema_value(item) for item in value]

    if not isinstance(value, dict):
        return value

    result: dict[str, object] = {}

    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError("JSON-schema object keys must be strings.")

        if key in {
            "default",
            "title",
        }:
            continue

        result[key] = _normalize_schema_value(item)

    if result.get("type") == "object":
        properties = result.get("properties")

        if isinstance(properties, dict):
            property_names = [key for key in properties if isinstance(key, str)]
            result["required"] = property_names
            result["additionalProperties"] = False

    return result


def _parse_openai_usage(
    value: object,
) -> ProviderUsage | None:
    """Parse OpenAI Responses API token usage."""

    if value is None:
        return None

    if not isinstance(value, dict):
        raise ProviderTransportError(
            "OpenAI response field 'usage' must be an object.",
            retryable=False,
        )

    input_tokens = value.get("input_tokens")
    output_tokens = value.get("output_tokens")

    if not isinstance(
        input_tokens,
        int,
    ):
        raise ProviderTransportError(
            "OpenAI usage.input_tokens must be an integer.",
            retryable=False,
        )

    if not isinstance(
        output_tokens,
        int,
    ):
        raise ProviderTransportError(
            "OpenAI usage.output_tokens must be an integer.",
            retryable=False,
        )

    return ProviderUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _parse_usage(
    value: object,
) -> ProviderUsage | None:
    """Parse generic transport usage metadata."""

    if value is None:
        return None

    if not isinstance(value, dict):
        raise ProviderTransportError(
            "Structured model endpoint field 'usage' must be an object.",
            retryable=False,
        )

    return ProviderUsage.model_validate(_string_key_dict(value))


def _optional_string(
    value: object,
    *,
    field_name: str,
) -> str | None:
    """Parse one optional normalized string field."""

    if value is None:
        return None

    if not isinstance(value, str):
        raise ProviderTransportError(
            f"Structured model endpoint field {field_name!r} must be a string.",
            retryable=False,
        )

    return value.strip() or None


def _string_key_dict(
    value: dict[object, object],
) -> dict[str, object]:
    """Return a dictionary while rejecting non-string keys."""

    result: dict[str, object] = {}

    for key, item in value.items():
        if not isinstance(key, str):
            raise ProviderTransportError(
                "Structured model endpoint returned a non-string object key.",
                retryable=False,
            )

        result[key] = item

    return result
