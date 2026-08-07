"""Query-service abstraction for the AeroRAG-X HTTP API."""

from __future__ import annotations

from typing import Protocol

from aeroragx.generation.grounded import (
    GroundedAnswer,
    GroundedAnswerGenerator,
)
from aeroragx.runtime import (
    RuntimeConfig,
    load_grounded_runtime,
)


class QueryService(Protocol):
    """Service interface required by the HTTP API."""

    def query(
        self,
        query: str,
    ) -> GroundedAnswer:
        """Generate one grounded answer."""

        ...


class GroundedAnswerQueryService:
    """Adapt GroundedAnswerGenerator to the HTTP query interface."""

    def __init__(
        self,
        generator: GroundedAnswerGenerator,
        *,
        reranker_model: str | None = None,
    ) -> None:
        self._generator = generator
        self._reranker_model = reranker_model

    def query(
        self,
        query: str,
    ) -> GroundedAnswer:
        """Generate one grounded answer."""

        return self._generator.generate(
            query,
            reranker_model=self._reranker_model,
        )


def load_query_service(
    config: RuntimeConfig,
) -> GroundedAnswerQueryService:
    """Construct the production HTTP query service."""

    runtime = load_grounded_runtime(config)

    return GroundedAnswerQueryService(
        runtime.generator,
        reranker_model=(runtime.reranker_settings.model_name),
    )
