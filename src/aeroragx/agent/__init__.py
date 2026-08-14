"""Bounded agent contracts and tool wrappers for AeroRAG-X."""

from aeroragx.agent.contracts import (
    AgentToolError,
    AgentToolName,
    CheckEvidenceSufficiencyRequest,
    CheckEvidenceSufficiencyResult,
    CompareSourcesRequest,
    CompareSourcesResult,
    EvidenceReference,
    FetchSourceContextRequest,
    FetchSourceContextResult,
    HybridRetrieveRequest,
    HybridRetrieveResult,
    SourceComparisonRecord,
    SourceContextRecord,
    SufficiencyAssessment,
    ToolCallRecord,
    ValidateCitationsRequest,
    ValidateCitationsResult,
)
from aeroragx.agent.registry import (
    AgentToolDefinition,
    AgentToolRegistry,
    build_default_agent_tool_registry,
)
from aeroragx.agent.state import (
    AgentFailureRecord,
    AgentState,
    AgentTerminationReason,
)
from aeroragx.agent.tools import (
    check_evidence_sufficiency,
    compare_sources,
    fetch_source_context,
    hybrid_retrieve,
    validate_citations,
)

__all__ = [
    "AgentFailureRecord",
    "AgentState",
    "AgentTerminationReason",
    "AgentToolDefinition",
    "AgentToolError",
    "AgentToolName",
    "AgentToolRegistry",
    "CheckEvidenceSufficiencyRequest",
    "CheckEvidenceSufficiencyResult",
    "CompareSourcesRequest",
    "CompareSourcesResult",
    "EvidenceReference",
    "FetchSourceContextRequest",
    "FetchSourceContextResult",
    "HybridRetrieveRequest",
    "HybridRetrieveResult",
    "SourceComparisonRecord",
    "SourceContextRecord",
    "SufficiencyAssessment",
    "ToolCallRecord",
    "ValidateCitationsRequest",
    "ValidateCitationsResult",
    "build_default_agent_tool_registry",
    "check_evidence_sufficiency",
    "compare_sources",
    "fetch_source_context",
    "hybrid_retrieve",
    "validate_citations",
]
