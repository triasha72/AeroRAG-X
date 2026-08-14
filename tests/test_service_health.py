"""Tests for container service health contracts."""

from fastapi.testclient import TestClient

from services.retrieval_service.app import create_app


def test_unconfigured_retrieval_service_is_live_but_not_ready() -> None:
    client = TestClient(create_app())
    assert client.get("/health/live").json()["ready"] is True
    assert client.get("/health/ready").json()["ready"] is False
