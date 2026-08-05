import httpx
import pytest

from aeroragx.ingestion.ntrs import NTRSClient, records_to_json_rows


def test_search_by_title_parses_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["title"] == "thermal management"
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
        records = client.search_by_title("thermal management", limit=1)

    assert records[0].document_id == 20240012345
    assert records[0].downloads_available is True
    assert records_to_json_rows(records)[0]["title"].startswith("Thermal")


def test_search_by_title_rejects_blank_query() -> None:
    with NTRSClient(transport=httpx.MockTransport(lambda _: httpx.Response(200))) as client:
        with pytest.raises(ValueError, match="cannot be empty"):
            client.search_by_title("   ")
