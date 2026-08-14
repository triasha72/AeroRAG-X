"""Tests for bounded retry classification and policy."""

from aeroragx.agent.failure_policy import AgentFailurePolicy, ToolRetryRule
from aeroragx.agent.retry import classify_error_message


def test_classification_prefers_timeout() -> None:
    assert classify_error_message("request timeout") == "timeout"


def test_policy_defaults_to_zero_retries() -> None:
    policy = AgentFailurePolicy(
        rules={"hybrid_retrieve": [ToolRetryRule(failure_class="timeout", maximum_retries=1)]}
    )
    assert policy.retries_for("hybrid_retrieve", "service_error") == 0
