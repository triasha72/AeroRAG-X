"""Structured JSON logging utilities for AeroRAG-X."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TextIO

_EVENT_KEY = "aeroragx_event"
_FIELDS_KEY = "aeroragx_fields"

_RESERVED_FIELDS = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "event",
        "exception",
    }
)


class JsonLogFormatter(logging.Formatter):
    """Format one logging record as one compact JSON object."""

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        """Return a stable JSON representation of one log record."""

        timestamp = (
            datetime.fromtimestamp(
                record.created,
                tz=UTC,
            )
            .isoformat(
                timespec="milliseconds",
            )
            .replace(
                "+00:00",
                "Z",
            )
        )

        raw_event: object = getattr(
            record,
            _EVENT_KEY,
            record.getMessage(),
        )

        event = (
            raw_event if isinstance(raw_event, str) and raw_event.strip() else record.getMessage()
        )

        payload: dict[str, object] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "event": event,
        }

        raw_fields: object = getattr(
            record,
            _FIELDS_KEY,
            {},
        )

        if isinstance(raw_fields, Mapping):
            for raw_key, value in raw_fields.items():
                if not isinstance(raw_key, str):
                    continue

                key = raw_key.strip()

                if not key or key in _RESERVED_FIELDS:
                    continue

                payload[key] = value

        if record.exc_info is not None:
            payload["exception"] = self.formatException(
                record.exc_info,
            )

        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        )


def configure_json_logger(
    *,
    name: str = "aeroragx",
    level: int = logging.INFO,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Configure one AeroRAG-X logger for line-delimited JSON output."""

    logger = logging.getLogger(name)

    handler = logging.StreamHandler(
        stream,
    )
    handler.setFormatter(
        JsonLogFormatter(),
    )

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    **fields: object,
) -> None:
    """Emit one structured AeroRAG-X event without logging raw payloads."""

    normalized_event = event.strip()

    if not normalized_event:
        raise ValueError("event must not be blank.")

    logger.log(
        level,
        normalized_event,
        extra={
            _EVENT_KEY: normalized_event,
            _FIELDS_KEY: fields,
        },
    )
