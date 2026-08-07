"""Tests for the AeroRAG-X FastAPI application."""

from __future__ import annotations

from fastapi.testclient import TestClient

from aeroragx.api import create_app
from aeroragx.generation.grounded import (
    GroundedAnswer,
    GroundedClaim,
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

    assert response.json() == {"detail": ("AeroRAG-X runtime is not ready.")}


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
