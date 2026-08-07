"""Tests for the AeroRAG-X FastAPI application."""

from __future__ import annotations

from fastapi.testclient import TestClient

from aeroragx.api import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }


def test_ready_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "ready": True,
    }


def test_openapi_document_is_available() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert schema["info"]["title"] == ("AeroRAG-X")

    assert "/health" in schema["paths"]
    assert "/ready" in schema["paths"]
