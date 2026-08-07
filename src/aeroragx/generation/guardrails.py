"""Deterministic guardrails for retrieved evidence."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.generation.prompting import ProviderHardeningConfig
from aeroragx.generation.provider import ProviderEvidence


class PromptInjectionFinding(BaseModel):
    """One suspicious instruction-like pattern in evidence."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    matched_text: str = Field(min_length=1)


class PromptInjectionAssessment(BaseModel):
    """Result of scanning retrieved evidence for prompt injection."""

    model_config = ConfigDict(extra="forbid")

    safe: bool
    findings: list[PromptInjectionFinding]


_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignore_instructions",
        re.compile(
            r"\bignore\s+(?:all\s+)?(?:previous|prior|system|developer)"
            r"\s+instructions?\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "override_system_prompt",
        re.compile(
            r"\b(?:override|replace|change)\s+(?:the\s+)?system\s+prompt\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "reveal_hidden_prompt",
        re.compile(
            r"\b(?:reveal|show|print|expose)\s+(?:the\s+)?(?:hidden\s+)?"
            r"(?:system|developer)\s+(?:prompt|message|instructions?)\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "developer_message",
        re.compile(r"\bdeveloper\s+message\b", flags=re.IGNORECASE),
    ),
    (
        "tool_execution",
        re.compile(
            r"\b(?:execute|run|call)\s+(?:this\s+)?"
            r"(?:tool|command|shell|code)\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "role_reassignment",
        re.compile(r"\byou\s+are\s+now\b", flags=re.IGNORECASE),
    ),
)


def assess_prompt_injection(
    evidence: Sequence[ProviderEvidence],
) -> PromptInjectionAssessment:
    """Scan evidence for deterministic instruction-like patterns."""

    findings: list[PromptInjectionFinding] = []

    for item in evidence:
        for rule_id, pattern in _RULES:
            match = pattern.search(item.text)

            if match is None:
                continue

            findings.append(
                PromptInjectionFinding(
                    evidence_id=item.evidence_id,
                    rule_id=rule_id,
                    matched_text=match.group(0),
                )
            )

    return PromptInjectionAssessment(
        safe=not findings,
        findings=findings,
    )


def enforce_prompt_injection_policy(
    *,
    evidence: Sequence[ProviderEvidence],
    config: ProviderHardeningConfig,
) -> PromptInjectionAssessment:
    """Assess evidence and enforce the configured policy."""

    assessment = assess_prompt_injection(evidence)

    if not assessment.safe and config.prompt_injection_policy == "block":
        rule_ids = sorted({finding.rule_id for finding in assessment.findings})
        raise ValueError(
            "Retrieved evidence failed prompt-injection guardrails: " + ", ".join(rule_ids)
        )

    return assessment
