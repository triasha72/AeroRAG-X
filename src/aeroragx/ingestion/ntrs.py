"""NASA Technical Reports Server OpenAPI client."""

from collections.abc import Iterable
from typing import Any
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field

NTRS_WEB_BASE_URL = "https://ntrs.nasa.gov"


class NTRSCenter(BaseModel):
    """NASA center associated with an NTRS record."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    code: str | None = None
    name: str | None = None


class NTRSDownloadLinks(BaseModel):
    """Download links returned by the NASA NTRS API."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    original: str | None = None
    pdf: str | None = None
    fulltext: str | None = None


class NTRSDownload(BaseModel):
    """Downloadable file associated with an NTRS record."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str
    mimetype: str | None = None
    type: str | None = None
    links: NTRSDownloadLinks = Field(default_factory=NTRSDownloadLinks)


class NTRSRecord(BaseModel):
    """Normalized subset of a NASA NTRS citation record."""

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    document_id: int = Field(alias="id")
    title: str
    abstract: str | None = None
    downloads_available: bool | None = Field(
        default=None,
        alias="downloadsAvailable",
    )
    keywords: list[str] = Field(default_factory=list)
    subject_categories: list[str] = Field(
        default_factory=list,
        alias="subjectCategories",
    )
    sti_type: str | None = Field(default=None, alias="stiType")
    distribution: str | None = None
    disseminated: str | None = None
    center: NTRSCenter | None = None
    downloads: list[NTRSDownload] = Field(default_factory=list)

    @property
    def citation_url(self) -> str:
        """Return the public NTRS citation page."""

        return f"{NTRS_WEB_BASE_URL}/citations/{self.document_id}"

    def pdf_url(self) -> str | None:
        """Return the first available PDF URL."""

        for download in self.downloads:
            candidate = download.links.pdf

            if candidate is None and (
                download.mimetype == "application/pdf" or download.name.lower().endswith(".pdf")
            ):
                candidate = download.links.original

            if candidate:
                return urljoin(f"{NTRS_WEB_BASE_URL}/", candidate)

        return None

    def fulltext_url(self) -> str | None:
        """Return the first available plain-text document URL."""

        for download in self.downloads:
            if download.links.fulltext:
                return urljoin(
                    f"{NTRS_WEB_BASE_URL}/",
                    download.links.fulltext,
                )

        return None


class NTRSClient:
    """Synchronous client for NASA NTRS citation search."""

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

    def search_by_title(
        self,
        title: str,
        limit: int = 10,
    ) -> list[NTRSRecord]:
        """Search public NASA citation records by title text."""

        normalized_title = title.strip()

        if not normalized_title:
            raise ValueError("Title query cannot be empty.")

        return self._search(
            search_parameters={"title": normalized_title},
            limit=limit,
            page_size=min(limit, 100),
        )

    def search(
        self,
        query: str,
        limit: int = 100,
        page_size: int = 50,
    ) -> list[NTRSRecord]:
        """Search NTRS using a free-text query with pagination."""

        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError("Search query cannot be empty.")

        return self._search(
            search_parameters={"q": normalized_query},
            limit=limit,
            page_size=page_size,
        )

    def _search(
        self,
        search_parameters: dict[str, str],
        limit: int,
        page_size: int,
    ) -> list[NTRSRecord]:
        """Execute a paginated citation search."""

        if limit < 1:
            raise ValueError("Limit must be at least 1.")

        if not 1 <= page_size <= 100:
            raise ValueError("Page size must be between 1 and 100.")

        collected: list[NTRSRecord] = []
        offset = 0

        while len(collected) < limit:
            request_size = min(page_size, limit - len(collected))

            request_parameters: dict[str, str | int] = {
                **search_parameters,
                "page.size": request_size,
                "page.from": offset,
                "sort.field": "id",
                "sort.order": "asc",
            }

            response = self._client.get(
                "/citations/search",
                params=request_parameters,
            )
            response.raise_for_status()

            payload: Any = response.json()
            raw_records = self._extract_records(payload)

            if not raw_records:
                break

            page_records = [NTRSRecord.model_validate(record) for record in raw_records]

            collected.extend(page_records)
            offset += len(raw_records)

            total = self._extract_total(payload)

            if total is not None and offset >= total:
                break

            if len(raw_records) < request_size:
                break

        return collected[:limit]

    @staticmethod
    def _extract_records(payload: Any) -> list[dict[str, Any]]:
        """Extract citation records from supported response wrappers."""

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            raise ValueError("Unexpected NTRS response type.")

        for key in ("results", "items", "citations"):
            value = payload.get(key)

            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        raise ValueError("NTRS response did not contain a citation list.")

    @staticmethod
    def _extract_total(payload: Any) -> int | None:
        """Extract the total result count when NASA provides it."""

        if not isinstance(payload, dict):
            return None

        stats = payload.get("stats")

        if not isinstance(stats, dict):
            return None

        total = stats.get("total")

        if isinstance(total, bool):
            return None

        if isinstance(total, int):
            return total

        return None


def records_to_json_rows(
    records: Iterable[NTRSRecord],
) -> list[dict[str, Any]]:
    """Serialize records using readable Python field names."""

    return [record.model_dump(mode="json") for record in records]
