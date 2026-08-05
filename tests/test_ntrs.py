import httpx
import pytest

from aeroragx.ingestion.ntrs import (
    NTRSClient,
    NTRSRecord,
    records_to_json_rows,
)


def test_search_by_title_parses_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["title"] == "thermal management"
        assert request.url.params["page.from"] == "0"

        return httpx.Response(
            200,
            json={
                "stats": {"total": 1},
                "results": [
                    {
                        "id": 20240012345,
                        "title": "Thermal Management for Electric Aircraft",
                        "abstract": "A technical study.",
                        "downloadsAvailable": True,
                        "keywords": ["thermal management"],
                        "subjectCategories": ["Aircraft Propulsion and Power"],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    with NTRSClient(transport=transport) as client:
        records = client.search_by_title(
            "thermal management",
            limit=1,
        )

    assert records[0].document_id == 20240012345
    assert records[0].downloads_available is True
    assert records_to_json_rows(records)[0]["title"].startswith("Thermal")


def test_search_by_title_rejects_blank_query() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200))

    with NTRSClient(transport=transport) as client:
        with pytest.raises(
            ValueError,
            match="cannot be empty",
        ):
            client.search_by_title("   ")


def test_free_text_search_uses_pagination() -> None:
    requested_offsets: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["page.from"])
        requested_offsets.append(offset)

        assert request.url.params["q"] == "electric aircraft"
        assert request.url.params["sort.field"] == "id"
        assert request.url.params["sort.order"] == "asc"

        if offset == 0:
            return httpx.Response(
                200,
                json={
                    "stats": {"total": 3},
                    "results": [
                        {
                            "id": 100,
                            "title": "Report One",
                        },
                        {
                            "id": 101,
                            "title": "Report Two",
                        },
                    ],
                },
            )

        return httpx.Response(
            200,
            json={
                "stats": {"total": 3},
                "results": [
                    {
                        "id": 102,
                        "title": "Report Three",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    with NTRSClient(transport=transport) as client:
        records = client.search(
            "electric aircraft",
            limit=3,
            page_size=2,
        )

    assert requested_offsets == [0, 2]
    assert [record.document_id for record in records] == [
        100,
        101,
        102,
    ]


def test_record_resolves_document_links() -> None:
    record = NTRSRecord.model_validate(
        {
            "id": 20240015017,
            "title": "Thermoacoustic Thermal Management",
            "downloadsAvailable": True,
            "downloads": [
                {
                    "name": "technical-report.pdf",
                    "mimetype": "application/pdf",
                    "links": {
                        "pdf": ("/api/citations/20240015017/downloads/technical-report.pdf"),
                        "fulltext": ("/api/citations/20240015017/downloads/technical-report.txt"),
                    },
                }
            ],
        }
    )

    assert record.citation_url == ("https://ntrs.nasa.gov/citations/20240015017")
    assert record.pdf_url() == (
        "https://ntrs.nasa.gov/api/citations/20240015017/downloads/technical-report.pdf"
    )
    assert record.fulltext_url() == (
        "https://ntrs.nasa.gov/api/citations/20240015017/downloads/technical-report.txt"
    )


def test_search_rejects_invalid_page_size() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200))

    with NTRSClient(transport=transport) as client:
        with pytest.raises(
            ValueError,
            match="between 1 and 100",
        ):
            client.search(
                "electric aircraft",
                page_size=101,
            )
