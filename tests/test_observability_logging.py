"""Tests for AeroRAG-X structured JSON logging."""

from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path

import pytest

from aeroragx.observability.logging import (
    JsonLogFormatter,
    configure_json_logger,
    log_event,
)


def test_json_formatter_emits_stable_core_fields() -> None:
    formatter = JsonLogFormatter()

    record = logging.LogRecord(
        name="aeroragx.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="fallback_event",
        args=(),
        exc_info=None,
    )

    rendered = formatter.format(record)
    payload = json.loads(rendered)

    assert payload["event"] == "fallback_event"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "aeroragx.test"
    assert payload["timestamp"].endswith("Z")


def test_log_event_emits_custom_structured_fields() -> None:
    stream = StringIO()

    logger = configure_json_logger(
        name="aeroragx.test.structured",
        stream=stream,
    )

    log_event(
        logger,
        "http_request_completed",
        request_id="request-123",
        method="POST",
        path="/v1/query",
        status_code=200,
        duration_ms=12.5,
    )

    payload = json.loads(
        stream.getvalue(),
    )

    assert payload["event"] == "http_request_completed"
    assert payload["request_id"] == "request-123"
    assert payload["method"] == "POST"
    assert payload["path"] == "/v1/query"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.5


def test_reserved_core_fields_cannot_be_overridden() -> None:
    stream = StringIO()

    logger = configure_json_logger(
        name="aeroragx.test.reserved",
        stream=stream,
    )

    log_event(
        logger,
        "safe_event",
        timestamp="not-a-timestamp",
        exception="not-an-exception",
        level_name="not-a-level",
    )

    payload = json.loads(
        stream.getvalue(),
    )

    assert payload["event"] == "safe_event"
    assert payload["logger"] == "aeroragx.test.reserved"
    assert payload["timestamp"] != "not-a-timestamp"
    assert "exception" not in payload
    assert payload["level_name"] == "not-a-level"


def test_non_json_native_values_are_stringified() -> None:
    stream = StringIO()

    logger = configure_json_logger(
        name="aeroragx.test.serialization",
        stream=stream,
    )

    log_event(
        logger,
        "runtime_configuration",
        config_path=Path("configs/generation_v0_1.yaml"),
    )

    payload = json.loads(
        stream.getvalue(),
    )

    assert payload["config_path"] == "configs/generation_v0_1.yaml"


def test_configure_json_logger_replaces_existing_handlers() -> None:
    logger_name = "aeroragx.test.handlers"

    logger = logging.getLogger(
        logger_name,
    )
    logger.handlers.clear()
    logger.addHandler(
        logging.NullHandler(),
    )

    stream = StringIO()

    configured = configure_json_logger(
        name=logger_name,
        stream=stream,
    )

    assert configured is logger
    assert len(configured.handlers) == 1
    assert isinstance(
        configured.handlers[0].formatter,
        JsonLogFormatter,
    )
    assert configured.propagate is False


def test_blank_event_is_rejected() -> None:
    logger = configure_json_logger(
        name="aeroragx.test.blank",
        stream=StringIO(),
    )

    with pytest.raises(
        ValueError,
        match="event must not be blank",
    ):
        log_event(
            logger,
            "   ",
        )
