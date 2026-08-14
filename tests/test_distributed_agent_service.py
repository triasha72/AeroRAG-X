"""Tests for distributed agent safe behavior."""

import asyncio

from aeroragx.services.contracts import (
    AgentServiceRequest,
    InferenceServiceResponse,
    RetrievalServiceResponse,
    ServiceEvidence,
)
from aeroragx.services.distributed_agent import DistributedAgentService
from aeroragx.services.request_context import RequestContext


class RetrievalClient:
    async def retrieve(self, request):  # type: ignore[no-untyped-def]
        return RetrievalServiceResponse(
            context=request.context,
            evidence=[
                ServiceEvidence(
                    evidence_id="e1",
                    document_id=123,
                    text="context",
                    citation_url="https://example.com/citation",
                )
            ],
        )


class InferenceClient:
    async def generate(self, request):  # type: ignore[no-untyped-def]
        return InferenceServiceResponse(
            context=request.context,
            answer="answer",
            cited_evidence_ids=["e1"],
        )


def test_distributed_agent_preserves_grounded_citations() -> None:
    service = DistributedAgentService(
        retrieval_client=RetrievalClient(),  # type: ignore[arg-type]
        inference_client=InferenceClient(),  # type: ignore[arg-type]
    )
    context = RequestContext(
        request_id="r1",
        trace_id="trace1",
        thread_id="thread1",
    )
    response = asyncio.run(service.query(AgentServiceRequest(context=context, query="q")))
    assert response.termination_reason == "answer_completed"
    assert response.cited_evidence_ids == ["e1"]
