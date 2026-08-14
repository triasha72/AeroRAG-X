"""Minimal distributed orchestration adapter over retrieval and inference services."""

from __future__ import annotations

from aeroragx.services.clients import (
    InferenceServiceClient,
    RetrievalServiceClient,
)
from aeroragx.services.contracts import (
    AgentServiceRequest,
    AgentServiceResponse,
    InferenceServiceRequest,
    RetrievalServiceRequest,
)


class DistributedAgentService:
    """Compose remote retrieval and inference while preserving request identity."""

    def __init__(
        self,
        *,
        retrieval_client: RetrievalServiceClient,
        inference_client: InferenceServiceClient,
    ) -> None:
        self._retrieval_client = retrieval_client
        self._inference_client = inference_client

    async def query(self, request: AgentServiceRequest) -> AgentServiceResponse:
        retrieval = await self._retrieval_client.retrieve(
            RetrievalServiceRequest(
                context=request.context,
                query=request.query,
            )
        )

        if not retrieval.evidence:
            return AgentServiceResponse(
                context=request.context,
                answer=None,
                termination_reason="grounded_refusal",
            )

        generation = await self._inference_client.generate(
            InferenceServiceRequest(
                context=request.context,
                query=request.query,
                evidence=retrieval.evidence,
            )
        )

        known_ids = {item.evidence_id for item in retrieval.evidence}
        cited_ids = generation.cited_evidence_ids
        if any(evidence_id not in known_ids for evidence_id in cited_ids):
            return AgentServiceResponse(
                context=request.context,
                answer=None,
                termination_reason="citation_validation_failure",
            )

        return AgentServiceResponse(
            context=request.context,
            answer=generation.answer,
            cited_evidence_ids=cited_ids,
            termination_reason="answer_completed",
        )
