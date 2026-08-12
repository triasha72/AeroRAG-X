"""Runtime-selection tests for Phase 29 LangGraph adaptive retrieval."""

from __future__ import annotations

from typing import cast

import pytest

from aeroragx.api.settings import load_api_runtime_settings
from aeroragx.generation.adaptive_retrieval import (
    AdaptiveRetrievalConfig,
    BoundedAdaptiveRetrievalController,
)
from aeroragx.generation.grounded import (
    AdaptiveRetrievalOrchestrator,
    GenerationConfig,
    GenerationProvider,
    GroundedAnswerGenerator,
    RerankedEvidenceIndex,
)
from aeroragx.orchestration.langgraph_adaptive import (
    LangGraphBoundedAdaptiveRetrievalController,
)


def _generator(
    orchestrator: str = "native",
) -> GroundedAnswerGenerator:
    """Create a generator without exercising retrieval or provider calls."""

    return GroundedAnswerGenerator(
        index=cast(RerankedEvidenceIndex, object()),
        provider=cast(GenerationProvider, object()),
        config=GenerationConfig(
            provider="test",
            model_name="test-model",
        ),
        adaptive_retrieval_config=AdaptiveRetrievalConfig(),
        adaptive_retrieval_orchestrator=cast(
            AdaptiveRetrievalOrchestrator,
            orchestrator,
        ),
    )


def test_native_orchestrator_remains_the_default() -> None:
    """Native bounded retrieval remains the safe default."""

    generator = _generator()

    assert generator.adaptive_retrieval_orchestrator == "native"
    assert isinstance(
        generator._adaptive_retrieval,
        BoundedAdaptiveRetrievalController,
    )


def test_langgraph_orchestrator_is_explicitly_opt_in() -> None:
    """LangGraph is constructed only after an explicit selection."""

    generator = _generator("langgraph")

    assert generator.adaptive_retrieval_orchestrator == "langgraph"
    assert isinstance(
        generator._adaptive_retrieval,
        LangGraphBoundedAdaptiveRetrievalController,
    )


def test_api_environment_selects_langgraph() -> None:
    """The API environment value reaches RuntimeConfig."""

    settings = load_api_runtime_settings(
        {
            "AERORAGX_ENABLE_ADAPTIVE_RETRIEVAL": "true",
            "AERORAGX_ADAPTIVE_RETRIEVAL_ORCHESTRATOR": "langgraph",
        }
    )

    runtime_config = settings.to_runtime_config()

    assert settings.adaptive_retrieval_enabled is True
    assert settings.adaptive_retrieval_orchestrator == "langgraph"
    assert runtime_config.adaptive_retrieval_orchestrator == "langgraph"


def test_api_rejects_unknown_orchestrator() -> None:
    """Invalid environment values fail before runtime construction."""

    with pytest.raises(
        ValueError,
        match="AERORAGX_ADAPTIVE_RETRIEVAL_ORCHESTRATOR",
    ):
        load_api_runtime_settings(
            {
                "AERORAGX_ADAPTIVE_RETRIEVAL_ORCHESTRATOR": "unknown",
            }
        )
