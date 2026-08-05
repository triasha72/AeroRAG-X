"""NASA Technical Reports Server OpenAPI client."""

from collections.abc import Iterable
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


class NTRSRecord(BaseModel):
    """Normalized subset of a NASA NTRS citation record."""

    model_config = ConfigDict(extra="ignore")

    document_id: int = Field(alias="id")
    title: str
    abstract: str | None = None
    downloads_available: bool | None = Field(default=None, alias="downloadsAvailable")
    keywords: list[str] = Field(default_factory=list)
    subject_categories: list[str] = Field(default_factory=list, alias="subjectCategories")


class NTRSClient:
    """Small synchronous client for NASA NTRS citation search."""

    def __init__(
        self,
        base_url: str = "https://ntrs.nasa.gov/api",
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            transport=transport,
            headers={"User-Agent": "AeroRAG-X/0.1"},
        )

    def __enter__(self) -> "NTRSClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def search_by_title(self, title: str, limit: int = 10) -> list[NTRSRecord]:
        """Search public NASA citation records by title text."""
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError("Title query cannot be empty.")
        if limit < 1:
            raise ValueError("Limit must be at least 1.")

        response = self._client.get("/citations/search", params={"title": normalized_title})
        response.raise_for_status()
        payload = response.json()
        records = self._extract_records(payload)
        return [NTRSRecord.model_validate(item) for item in records[:limit]]

    @staticmethod
    def _extract_records(payload: Any) -> list[dict[str, Any]]:
        """Extract citation records while tolerating documented response wrappers."""
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            raise ValueError("Unexpected NTRS response type.")

        for key in ("results", "items", "citations"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        raise ValueError("NTRS response did not contain a citation list.")


def records_to_json_rows(records: Iterable[NTRSRecord]) -> list[dict[str, Any]]:
    """Serialize records using readable Python field names."""
    return [record.model_dump(mode="json") for record in records]
