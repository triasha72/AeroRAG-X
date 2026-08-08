"""Tests for the AeroRAG-X FastAPI application."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from aeroragx.api import create_app
from aeroragx.generation.grounded import (
    GroundedAnswer,
    GroundedClaim,
)
from aeroragx.observability import configure_json_logger


class FakeQueryService:
    """Deterministic query service for API tests."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    def query(
        self,
        query: str,
    ) -> GroundedAnswer:
        self.queries.append(query)

        return GroundedAnswer(
            query=query,
            answer=("A deterministic grounded test answer."),
            claims=[
                GroundedClaim(
                    claim_id="CL1",
                    text=("A deterministic grounded test claim."),
                    citation_ids=[],
                )
            ],
            citations=[],
            source_documents=[],
            insufficient_evidence=False,
            retrieval_metadata=None,
        )


def capturing_event_logger(
    name: str,
) -> tuple[logging.Logger, StringIO]:
    """Return one isolated structured logger and capture stream."""

    stream = StringIO()

    logger = configure_json_logger(
        name=name,
        stream=stream,
    )

    return logger, stream


def read_log_events(
    stream: StringIO,
) -> list[dict[str, object]]:
    """Parse line-delimited JSON events from one capture stream."""

    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


def test_not_ready_without_query_service() -> None:
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "not_ready",
        "ready": False,
    }


def test_ready_with_query_service() -> None:
    service = FakeQueryService()

    client = TestClient(create_app(query_service=service))

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "ready": True,
    }


def test_query_returns_service_answer() -> None:
    service = FakeQueryService()

    client = TestClient(create_app(query_service=service))

    response = client.post(
        "/v1/query",
        json={"query": ("Why is aircraft thermal management important?")},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == ("Why is aircraft thermal management important?")

    assert data["insufficient_evidence"] is False

    assert data["answer"] == ("A deterministic grounded test answer.")

    assert service.queries == [("Why is aircraft thermal management important?")]


def test_query_is_unavailable_without_service() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/query",
        json={"query": "test query"},
    )

    assert response.status_code == 503

    data = response.json()

    assert data["error"]["code"] == ("runtime_unavailable")

    assert data["error"]["message"] == ("AeroRAG-X runtime is not ready.")

    assert data["error"]["request_id"] == response.headers["x-request-id"]


def test_blank_query_is_rejected() -> None:
    service = FakeQueryService()

    client = TestClient(create_app(query_service=service))

    response = client.post(
        "/v1/query",
        json={"query": "   "},
    )

    assert response.status_code == 422


def test_missing_query_is_rejected() -> None:
    service = FakeQueryService()

    client = TestClient(create_app(query_service=service))

    response = client.post(
        "/v1/query",
        json={},
    )

    assert response.status_code == 422


def test_extra_request_field_is_rejected() -> None:
    service = FakeQueryService()

    client = TestClient(create_app(query_service=service))

    response = client.post(
        "/v1/query",
        json={
            "query": "test query",
            "unexpected": True,
        },
    )

    assert response.status_code == 422


def test_openapi_document_is_available() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert schema["info"]["title"] == ("AeroRAG-X")

    assert "/health" in schema["paths"]
    assert "/ready" in schema["paths"]
    assert "/v1/query" in schema["paths"]


def test_runtime_loader_sets_ready_during_lifespan() -> None:
    from aeroragx.api.service import QueryService
    from aeroragx.runtime import RuntimeConfig

    service = FakeQueryService()

    loaded_configs: list[RuntimeConfig] = []

    def fake_loader(
        config: RuntimeConfig,
    ) -> QueryService:
        loaded_configs.append(config)
        return service

    runtime_config = RuntimeConfig(
        candidate_top_k=20,
        evidence_top_k=5,
    )

    application = create_app(
        runtime_config=runtime_config,
        service_loader=fake_loader,
    )

    with TestClient(application) as client:
        readiness = client.get("/ready")

        assert readiness.status_code == 200

        assert readiness.json() == {
            "status": "ready",
            "ready": True,
        }

        response = client.post(
            "/v1/query",
            json={"query": ("Why is aircraft thermal management important?")},
        )

        assert response.status_code == 200

    assert loaded_configs == [runtime_config]


def test_runtime_loader_emits_structured_startup_events() -> None:
    from aeroragx.api.service import QueryService
    from aeroragx.runtime import RuntimeConfig

    service = FakeQueryService()
    logger, stream = capturing_event_logger(
        "aeroragx.test.api.runtime",
    )

    def fake_loader(
        config: RuntimeConfig,
    ) -> QueryService:
        assert config.candidate_top_k == 20
        assert config.evidence_top_k == 5

        return service

    runtime_config = RuntimeConfig(
        candidate_top_k=20,
        evidence_top_k=5,
    )

    application = create_app(
        runtime_config=runtime_config,
        service_loader=fake_loader,
        event_logger=logger,
    )

    with TestClient(application) as client:
        readiness = client.get("/ready")

        assert readiness.status_code == 200
        assert readiness.json()["ready"] is True

    events = read_log_events(stream)

    runtime_events = [event for event in events if str(event["event"]).startswith("runtime_load_")]

    assert [event["event"] for event in runtime_events] == [
        "runtime_load_started",
        "runtime_load_completed",
    ]

    started = runtime_events[0]
    completed = runtime_events[1]

    assert started["runtime_mode"] == "local"
    assert started["candidate_top_k"] == 20
    assert started["evidence_top_k"] == 5

    assert completed["runtime_mode"] == "local"
    assert completed["candidate_top_k"] == 20
    assert completed["evidence_top_k"] == 5
    assert completed["succeeded"] is True
    assert isinstance(completed["duration_ms"], float)
    assert completed["duration_ms"] >= 0.0


def test_runtime_loader_failure_emits_safe_failure_event() -> None:
    from aeroragx.api.service import QueryService
    from aeroragx.runtime import RuntimeConfig

    logger, stream = capturing_event_logger(
        "aeroragx.test.api.runtime.failure",
    )

    def failing_loader(
        config: RuntimeConfig,
    ) -> QueryService:
        del config

        raise RuntimeError("sensitive runtime failure detail")

    runtime_config = RuntimeConfig(
        candidate_top_k=20,
        evidence_top_k=5,
    )

    application = create_app(
        runtime_config=runtime_config,
        service_loader=failing_loader,
        event_logger=logger,
    )

    with pytest.raises(
        RuntimeError,
        match="sensitive runtime failure detail",
    ):
        with TestClient(application):
            pass

    events = read_log_events(stream)

    assert [event["event"] for event in events] == [
        "runtime_load_started",
        "runtime_load_failed",
    ]

    failed = events[-1]

    assert failed["level"] == "ERROR"
    assert failed["runtime_mode"] == "local"
    assert failed["candidate_top_k"] == 20
    assert failed["evidence_top_k"] == 5
    assert failed["succeeded"] is False
    assert failed["error_type"] == "RuntimeError"
    assert isinstance(failed["duration_ms"], float)
    assert failed["duration_ms"] >= 0.0

    assert "sensitive runtime failure detail" not in stream.getvalue()


def test_openai_runtime_is_identified_without_logging_secrets() -> None:
    from pathlib import Path

    from aeroragx.api.service import QueryService
    from aeroragx.runtime import RuntimeConfig

    service = FakeQueryService()
    logger, stream = capturing_event_logger(
        "aeroragx.test.api.runtime.openai",
    )

    def fake_loader(
        config: RuntimeConfig,
    ) -> QueryService:
        del config

        return service

    runtime_config = RuntimeConfig(
        provider_config=Path("configs/provider_v0_1.yaml"),
        candidate_top_k=20,
        evidence_top_k=5,
    )

    application = create_app(
        runtime_config=runtime_config,
        service_loader=fake_loader,
        event_logger=logger,
    )

    with TestClient(application):
        pass

    events = read_log_events(stream)

    runtime_events = [event for event in events if str(event["event"]).startswith("runtime_load_")]

    assert runtime_events[0]["runtime_mode"] == "openai"
    assert runtime_events[1]["runtime_mode"] == "openai"

    rendered = stream.getvalue()

    assert "OPENAI_API_KEY" not in rendered
    assert "Authorization" not in rendered
    assert "Bearer " not in rendered


def test_success_response_has_request_id() -> None:
    from uuid import UUID

    service = FakeQueryService()

    client = TestClient(create_app(query_service=service))

    response = client.post(
        "/v1/query",
        json={"query": "test query"},
    )

    assert response.status_code == 200

    request_id = response.headers["x-request-id"]

    UUID(request_id)


def test_validation_error_is_structured() -> None:
    from uuid import UUID

    service = FakeQueryService()

    client = TestClient(create_app(query_service=service))

    response = client.post(
        "/v1/query",
        json={"query": "   "},
    )

    assert response.status_code == 422

    data = response.json()

    assert data["error"]["code"] == ("invalid_request")

    assert data["error"]["request_id"] == response.headers["x-request-id"]

    UUID(data["error"]["request_id"])


def test_provider_failure_is_structured() -> None:
    from aeroragx.generation.structured_provider import (
        ProviderTransportError,
    )

    class ProviderFailureService:
        def query(
            self,
            query: str,
        ) -> GroundedAnswer:
            del query

            raise ProviderTransportError(
                "simulated provider failure",
                retryable=False,
            )

    client = TestClient(create_app(query_service=(ProviderFailureService())))

    response = client.post(
        "/v1/query",
        json={"query": "test query"},
    )

    assert response.status_code == 502

    data = response.json()

    assert data["error"]["code"] == ("provider_failure")

    assert data["error"]["request_id"] == response.headers["x-request-id"]


def test_unexpected_failure_is_structured() -> None:
    class UnexpectedFailureService:
        def query(
            self,
            query: str,
        ) -> GroundedAnswer:
            del query

            raise RuntimeError("simulated internal failure")

    client = TestClient(
        create_app(query_service=(UnexpectedFailureService())),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/v1/query",
        json={"query": "test query"},
    )

    assert response.status_code == 500

    data = response.json()

    assert data["error"]["code"] == ("internal_error")

    assert data["error"]["request_id"] == response.headers["x-request-id"]


def test_success_request_emits_structured_http_log() -> None:
    service = FakeQueryService()
    logger, stream = capturing_event_logger(
        "aeroragx.test.api.success",
    )

    client = TestClient(
        create_app(
            query_service=service,
            event_logger=logger,
        )
    )

    raw_query = "Why is aircraft thermal management important?"

    response = client.post(
        "/v1/query",
        json={"query": raw_query},
    )

    assert response.status_code == 200

    events = read_log_events(stream)

    assert len(events) == 1

    event = events[0]

    assert event["event"] == "http_request_completed"
    assert event["request_id"] == response.headers["x-request-id"]
    assert event["method"] == "POST"
    assert event["path"] == "/v1/query"
    assert event["status_code"] == 200
    assert event["succeeded"] is True
    assert isinstance(event["duration_ms"], float)
    assert event["duration_ms"] >= 0.0

    assert "query" not in event
    assert raw_query not in stream.getvalue()


def test_validation_error_emits_structured_http_log() -> None:
    service = FakeQueryService()
    logger, stream = capturing_event_logger(
        "aeroragx.test.api.validation",
    )

    client = TestClient(
        create_app(
            query_service=service,
            event_logger=logger,
        )
    )

    response = client.post(
        "/v1/query",
        json={"query": "   "},
    )

    assert response.status_code == 422

    events = read_log_events(stream)

    assert len(events) == 1

    event = events[0]

    assert event["event"] == "http_request_completed"
    assert event["request_id"] == response.headers["x-request-id"]
    assert event["method"] == "POST"
    assert event["path"] == "/v1/query"
    assert event["status_code"] == 422
    assert event["succeeded"] is False
    assert isinstance(event["duration_ms"], float)
    assert event["duration_ms"] >= 0.0
