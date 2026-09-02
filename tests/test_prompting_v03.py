"""Regression tests for the compact grounded JSON prompt."""

import json

from aeroragx.generation.prompting import ProviderHardeningConfig, build_grounded_prompt
from aeroragx.generation.provider import ProviderEvidence


def _prompt():
    return build_grounded_prompt(
        query="What does the evidence show?",
        evidence=[ProviderEvidence(evidence_id="E1", text="One supported fact.")],
        max_claims=4,
        config=ProviderHardeningConfig(
            version="0.3",
            prompt_version="grounded-json-v0.3-compact",
            prompt_injection_policy="block",
        ),
    )


def test_compact_prompt_keeps_schema_contract_in_system_rules() -> None:
    prompt = _prompt()
    assert "answer (string), claims" in prompt.system_prompt
    assert "one-sentence answer" in prompt.system_prompt
    assert "at most 4 short, atomic, non-overlapping claims" in prompt.system_prompt


def test_compact_payload_omits_redundant_schema_and_whitespace() -> None:
    prompt = _prompt()
    payload_text = prompt.user_prompt.split("\n", 1)[1].rsplit("\n", 1)[0]
    payload = json.loads(payload_text)
    assert "response_schema" not in payload
    assert "\n  " not in payload_text
    assert payload["evidence"][0]["evidence_id"] == "E1"


def test_compact_dev_prompt_uses_explicit_minimal_json_skeleton() -> None:
    prompt = build_grounded_prompt(
        query="What does the evidence show?",
        evidence=[ProviderEvidence(evidence_id="E1", text="One supported fact.")],
        max_claims=4,
        config=ProviderHardeningConfig(
            version="0.3.1",
            prompt_version="grounded-json-v0.3.1-compact-dev",
            prompt_injection_policy="block",
        ),
    )

    assert '"evidence_ids":["E1"]' in prompt.system_prompt
    assert "Return no markdown, code fence, prefix, suffix, or additional keys" in (
        prompt.system_prompt
    )
    payload_text = prompt.user_prompt.split("\n", 1)[1].rsplit("\n", 1)[0]
    assert "response_schema" not in json.loads(payload_text)
