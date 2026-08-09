"""Tests for the AeroRAG-X FastAPI application."""

from __future__ import annotations

import json
import logging
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import SpanKind

from aeroragx.api import create_app
from aeroragx.generation.grounded import (
    GroundedAnswer,
    GroundedClaim,
    RetrievalMetadata,
)
from aeroragx.generation.structured_provider import (
    ProviderTelemetry,
    ProviderUsage,
)
from aeroragx.observability import (
    configure_json_logger,
    create_tracing_runtime,
)


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

    http_events = [event for event in events if event["event"] == "http_request_completed"]

    assert len(http_events) == 1

    event = http_events[0]

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


def test_grounded_query_emits_structured_operational_telemetry() -> None:
    logger, stream = capturing_event_logger("aeroragx.test.api.query.telemetry")

    provider_telemetry = ProviderTelemetry(
        model_name="gpt-test",
        prompt_version="test-v1",
        attempts=2,
        latency_seconds=0.125,
        succeeded=True,
        request_id="provider-request-123",
        usage=ProviderUsage(input_tokens=120, output_tokens=30),
        estimated_cost_usd=0.00125,
        prompt_injection_safe=True,
        prompt_injection_findings=0,
        error_type=None,
    )

    metadata = RetrievalMetadata(
        retriever="cross_encoder_reranker",
        requested_evidence_top_k=5,
        returned_evidence_count=5,
        used_evidence_count=3,
        reranker_model="test-reranker",
        generation_provider="openai-responses",
        generation_model="gpt-test",
        evidence_sufficiency=None,
        provider_telemetry=provider_telemetry,
    )

    class TelemetryQueryService:
        def query(self, query: str) -> GroundedAnswer:
            return GroundedAnswer(
                query=query,
                answer="A grounded telemetry test answer.",
                claims=[
                    GroundedClaim(
                        claim_id="CL1",
                        text="A grounded telemetry test claim.",
                        citation_ids=[],
                    )
                ],
                citations=[],
                source_documents=[],
                insufficient_evidence=False,
                retrieval_metadata=metadata,
            )

    client = TestClient(
        create_app(
            query_service=TelemetryQueryService(),
            event_logger=logger,
        )
    )

    raw_query = "Explain the thermal-management result."
    response = client.post(
        "/v1/query",
        json={"query": raw_query},
    )

    assert response.status_code == 200

    query_event = next(
        event for event in read_log_events(stream) if event["event"] == "grounded_query_completed"
    )

    assert query_event["request_id"] == response.headers["x-request-id"]
    assert query_event["insufficient_evidence"] is False
    assert query_event["claim_count"] == 1
    assert query_event["retriever"] == "cross_encoder_reranker"
    assert query_event["returned_evidence_count"] == 5
    assert query_event["used_evidence_count"] == 3
    assert query_event["generation_provider"] == "openai-responses"
    assert query_event["generation_model"] == "gpt-test"
    assert query_event["provider_called"] is True
    assert query_event["provider_bypassed"] is False
    assert query_event["provider_succeeded"] is True
    assert query_event["provider_attempts"] == 2
    assert query_event["provider_latency_ms"] == 125.0
    assert query_event["provider_request_id"] == "provider-request-123"
    assert query_event["input_tokens"] == 120
    assert query_event["output_tokens"] == 30
    assert query_event["total_tokens"] == 150
    assert query_event["estimated_cost_usd"] == 0.00125
    assert query_event["prompt_injection_safe"] is True
    assert query_event["prompt_injection_findings"] == 0
    assert "query" not in query_event
    assert raw_query not in stream.getvalue()


def test_insufficient_answer_records_provider_bypass() -> None:
    logger, stream = capturing_event_logger("aeroragx.test.api.query.bypass")

    metadata = RetrievalMetadata(
        retriever="cross_encoder_reranker",
        requested_evidence_top_k=5,
        returned_evidence_count=0,
        used_evidence_count=0,
        reranker_model="test-reranker",
        generation_provider="fake",
        generation_model="deterministic-grounded-v0",
        evidence_sufficiency=None,
        provider_telemetry=None,
    )

    class InsufficientQueryService:
        def query(self, query: str) -> GroundedAnswer:
            return GroundedAnswer(
                query=query,
                answer="The retrieved evidence is insufficient to answer this question reliably.",
                claims=[],
                citations=[],
                source_documents=[],
                insufficient_evidence=True,
                retrieval_metadata=metadata,
            )

    client = TestClient(
        create_app(
            query_service=InsufficientQueryService(),
            event_logger=logger,
        )
    )

    response = client.post(
        "/v1/query",
        json={"query": "Unsupported aerospace claim"},
    )

    assert response.status_code == 200

    query_event = next(
        event for event in read_log_events(stream) if event["event"] == "grounded_query_completed"
    )

    assert query_event["insufficient_evidence"] is True
    assert query_event["provider_called"] is False
    assert query_event["provider_bypassed"] is True
    assert query_event["provider_attempts"] is None
    assert query_event["provider_latency_ms"] is None
    assert query_event["provider_request_id"] is None
    assert query_event["estimated_cost_usd"] is None


def test_query_without_retrieval_metadata_logs_safe_nulls() -> None:
    service = FakeQueryService()
    logger, stream = capturing_event_logger("aeroragx.test.api.query.no-metadata")

    client = TestClient(create_app(query_service=service, event_logger=logger))

    response = client.post(
        "/v1/query",
        json={"query": "test query"},
    )

    assert response.status_code == 200

    query_event = next(
        event for event in read_log_events(stream) if event["event"] == "grounded_query_completed"
    )

    assert query_event["retriever"] is None
    assert query_event["generation_provider"] is None
    assert query_event["provider_called"] is None
    assert query_event["provider_bypassed"] is None


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


def test_grounded_query_log_includes_internal_stage_timings() -> None:
    from aeroragx.generation.grounded import RAGStageTimings

    service = FakeQueryService()
    logger, stream = capturing_event_logger(
        "aeroragx.test.api.query.timings",
    )

    class TimedQueryService:
        def query(
            self,
            query: str,
        ) -> GroundedAnswer:
            answer = service.query(query)
            answer.attach_stage_timings(
                RAGStageTimings(
                    retrieval_ms=10.5,
                    bm25_ms=1.1,
                    dense_ms=3.2,
                    hybrid_fusion_ms=0.6,
                    reranker_scoring_ms=4.5,
                    retrieval_search_count=3,
                    facet_search_count=2,
                    facet_overhead_ms=1.1,
                    facet_used=True,
                    evidence_build_ms=0.8,
                    sufficiency_ms=0.4,
                    provider_stage_ms=125.0,
                    citation_resolution_ms=1.2,
                    total_ms=138.9,
                )
            )
            return answer

    client = TestClient(
        create_app(
            query_service=TimedQueryService(),
            event_logger=logger,
        )
    )

    response = client.post(
        "/v1/query",
        json={"query": "test query"},
    )

    assert response.status_code == 200
    assert "stage_timings" not in response.json()
    assert "_stage_timings" not in response.json()

    query_event = next(
        event for event in read_log_events(stream) if event["event"] == "grounded_query_completed"
    )

    assert query_event["retrieval_ms"] == 10.5
    assert query_event["bm25_ms"] == 1.1
    assert query_event["dense_ms"] == 3.2
    assert query_event["hybrid_fusion_ms"] == 0.6
    assert query_event["reranker_scoring_ms"] == 4.5
    assert query_event["retrieval_search_count"] == 3
    assert query_event["facet_search_count"] == 2
    assert query_event["facet_overhead_ms"] == 1.1
    assert query_event["facet_used"] is True
    assert query_event["evidence_build_ms"] == 0.8
    assert query_event["sufficiency_ms"] == 0.4
    assert query_event["provider_stage_ms"] == 125.0
    assert query_event["citation_resolution_ms"] == 1.2
    assert query_event["rag_total_ms"] == 138.9


def test_metrics_endpoint_exposes_http_and_query_metrics() -> None:
    service = FakeQueryService()
    client = TestClient(create_app(query_service=service))

    assert client.get("/health").status_code == 200
    assert (
        client.post(
            "/v1/query",
            json={"query": "metrics smoke test"},
        ).status_code
        == 200
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    rendered = response.text

    assert (
        "aeroragx_http_requests_total{"
        'method="GET",route="/health",status_class="2xx"} 1.0' in rendered
    )
    assert (
        "aeroragx_http_requests_total{"
        'method="POST",route="/v1/query",status_class="2xx"} 1.0' in rendered
    )
    assert "aeroragx_query_requests_total 1.0" in rendered
    assert "aeroragx_query_success_total 1.0" in rendered
    assert "aeroragx_query_errors_total 0.0" in rendered
    assert "metrics smoke test" not in rendered
    assert "request_id=" not in rendered


def test_metrics_record_rag_stage_histograms() -> None:
    from aeroragx.generation.grounded import RAGStageTimings

    service = FakeQueryService()

    class TimedMetricsQueryService:
        def query(self, query: str) -> GroundedAnswer:
            answer = service.query(query)
            answer.attach_stage_timings(
                RAGStageTimings(
                    retrieval_ms=400.0,
                    reranker_scoring_ms=200.0,
                    evidence_build_ms=20.0,
                    total_ms=1250.0,
                )
            )
            return answer

    client = TestClient(create_app(query_service=TimedMetricsQueryService()))

    assert (
        client.post(
            "/v1/query",
            json={"query": "timed metrics query"},
        ).status_code
        == 200
    )

    rendered = client.get("/metrics").text

    assert "aeroragx_rag_duration_seconds_count 1.0" in rendered
    assert "aeroragx_rag_duration_seconds_sum 1.25" in rendered
    assert "aeroragx_retrieval_duration_seconds_count 1.0" in rendered
    assert "aeroragx_retrieval_duration_seconds_sum 0.4" in rendered
    assert "aeroragx_reranker_duration_seconds_count 1.0" in rendered
    assert "aeroragx_reranker_duration_seconds_sum 0.2" in rendered


def test_metrics_record_provider_call_and_bypass() -> None:
    telemetry = ProviderTelemetry(
        model_name="gpt-test",
        prompt_version="test-v1",
        attempts=1,
        latency_seconds=0.75,
        succeeded=True,
        request_id="provider-metrics-request",
        usage=ProviderUsage(input_tokens=10, output_tokens=5),
        estimated_cost_usd=0.0001,
        prompt_injection_safe=True,
        prompt_injection_findings=0,
        error_type=None,
    )
    provider_metadata = RetrievalMetadata(
        retriever="cross_encoder_reranker",
        requested_evidence_top_k=5,
        returned_evidence_count=5,
        used_evidence_count=3,
        reranker_model="test-reranker",
        generation_provider="openai-responses",
        generation_model="gpt-test",
        evidence_sufficiency=None,
        provider_telemetry=telemetry,
    )

    class ProviderMetricsService:
        def query(self, query: str) -> GroundedAnswer:
            return GroundedAnswer(
                query=query,
                answer="provider metrics answer",
                claims=[
                    GroundedClaim(
                        claim_id="CL1",
                        text="provider metrics claim",
                        citation_ids=[],
                    )
                ],
                citations=[],
                source_documents=[],
                insufficient_evidence=False,
                retrieval_metadata=provider_metadata,
            )

    provider_client = TestClient(create_app(query_service=ProviderMetricsService()))
    assert (
        provider_client.post(
            "/v1/query",
            json={"query": "provider metrics"},
        ).status_code
        == 200
    )
    provider_rendered = provider_client.get("/metrics").text

    assert 'aeroragx_provider_calls_total{provider="openai-responses"} 1.0' in provider_rendered
    assert (
        "aeroragx_provider_duration_seconds_count{"
        'provider="openai-responses"} 1.0' in provider_rendered
    )

    bypass_metadata = RetrievalMetadata(
        retriever="cross_encoder_reranker",
        requested_evidence_top_k=5,
        returned_evidence_count=0,
        used_evidence_count=0,
        reranker_model="test-reranker",
        generation_provider="fake",
        generation_model="deterministic-grounded-v0",
        evidence_sufficiency=None,
        provider_telemetry=None,
    )

    class BypassMetricsService:
        def query(self, query: str) -> GroundedAnswer:
            return GroundedAnswer(
                query=query,
                answer=("The retrieved evidence is insufficient to answer this question reliably."),
                claims=[],
                citations=[],
                source_documents=[],
                insufficient_evidence=True,
                retrieval_metadata=bypass_metadata,
            )

    bypass_client = TestClient(create_app(query_service=BypassMetricsService()))
    assert (
        bypass_client.post(
            "/v1/query",
            json={"query": "unsupported metrics query"},
        ).status_code
        == 200
    )
    bypass_rendered = bypass_client.get("/metrics").text

    assert "aeroragx_insufficient_evidence_total 1.0" in bypass_rendered
    assert "aeroragx_provider_bypasses_total 1.0" in bypass_rendered


def test_metrics_record_query_and_provider_failures() -> None:
    from aeroragx.generation.structured_provider import ProviderTransportError

    class ProviderFailureMetricsService:
        def query(self, query: str) -> GroundedAnswer:
            del query
            raise ProviderTransportError(
                "simulated provider metrics failure",
                retryable=False,
            )

    client = TestClient(create_app(query_service=ProviderFailureMetricsService()))

    response = client.post(
        "/v1/query",
        json={"query": "provider failure metrics"},
    )
    rendered = client.get("/metrics").text

    assert response.status_code == 502
    assert "aeroragx_query_requests_total 1.0" in rendered
    assert "aeroragx_query_errors_total 1.0" in rendered
    assert 'aeroragx_provider_calls_total{provider="unknown"} 1.0' in rendered
    assert 'aeroragx_provider_errors_total{provider="unknown"} 1.0' in rendered
    assert (
        "aeroragx_http_requests_total{"
        'method="POST",route="/v1/query",status_class="5xx"} 1.0' in rendered
    )


def test_unmatched_metric_route_does_not_use_raw_path() -> None:
    client = TestClient(create_app())

    raw_path = "/unmatched/high-cardinality-value"
    assert client.get(raw_path).status_code == 404

    rendered = client.get("/metrics").text

    assert 'route="__unmatched__"' in rendered
    assert raw_path not in rendered


def test_query_trace_correlates_request_and_logs() -> None:
    exporter = InMemorySpanExporter()
    tracing_runtime = create_tracing_runtime(
        exporter=exporter,
        environment="test",
        batch_export=False,
    )
    service = FakeQueryService()
    logger, stream = capturing_event_logger(
        "aeroragx.test.api.tracing",
    )

    raw_query = "Sensitive tracing query text"

    application = create_app(
        query_service=service,
        event_logger=logger,
        tracing_runtime=tracing_runtime,
    )

    with TestClient(application) as client:
        response = client.post(
            "/v1/query",
            json={"query": raw_query},
        )

    assert response.status_code == 200

    tracing_runtime.force_flush()
    spans = exporter.get_finished_spans()

    query_span = next(span for span in spans if span.name == "aeroragx.query")
    server_span = next(span for span in spans if span.kind == SpanKind.SERVER)

    assert query_span.context is not None
    assert server_span.context is not None
    assert query_span.parent is not None

    assert query_span.context.trace_id == server_span.context.trace_id
    assert query_span.parent.span_id == server_span.context.span_id

    request_id = response.headers["x-request-id"]

    assert query_span.attributes["aeroragx.request_id"] == request_id
    assert query_span.attributes["aeroragx.insufficient_evidence"] is False
    assert query_span.attributes["aeroragx.claim_count"] == 1

    events = read_log_events(stream)

    query_event = next(event for event in events if event["event"] == "grounded_query_completed")
    http_event = next(event for event in events if event["event"] == "http_request_completed")

    expected_trace_id = f"{query_span.context.trace_id:032x}"
    expected_query_span_id = f"{query_span.context.span_id:016x}"
    expected_server_span_id = f"{server_span.context.span_id:016x}"

    assert query_event["request_id"] == request_id
    assert query_event["trace_id"] == expected_trace_id
    assert query_event["span_id"] == expected_query_span_id

    assert http_event["request_id"] == request_id
    assert http_event["trace_id"] == expected_trace_id
    assert http_event["span_id"] == expected_server_span_id

    serialized_attributes = repr(
        dict(query_span.attributes),
    )

    assert raw_query not in serialized_attributes
    assert raw_query not in stream.getvalue()

    tracing_runtime.shutdown()


def test_health_and_metrics_are_excluded_from_http_tracing() -> None:
    exporter = InMemorySpanExporter()
    tracing_runtime = create_tracing_runtime(
        exporter=exporter,
        environment="test",
        batch_export=False,
    )

    application = create_app(
        tracing_runtime=tracing_runtime,
    )

    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200

    tracing_runtime.force_flush()

    assert exporter.get_finished_spans() == ()

    tracing_runtime.shutdown()
