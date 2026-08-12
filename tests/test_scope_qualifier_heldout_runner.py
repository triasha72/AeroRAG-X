"""Tests for the Phase 28 held-out evaluation runner."""

from __future__ import annotations

from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = run_path(ROOT / "scripts/run_scope_qualifier_heldout_v01.py")
render_markdown = RUNNER["render_markdown"]


def test_render_markdown_includes_all_policy_conditions() -> None:
    baseline = {
        "single_pass": {
            "answerability_accuracy": 0.75,
            "unsupported_refusal_rate": 0.70,
        },
        "bounded_adaptive": {
            "answerability_accuracy": 0.75,
            "unsupported_refusal_rate": 0.80,
        },
        "summary": {
            "bounded_adaptive_false_refusal_count": 1,
            "bounded_adaptive_unsupported_generation_count": 2,
        },
    }
    scope_guard = {
        "single_pass": {
            "answerability_accuracy": 1.0,
            "unsupported_refusal_rate": 1.0,
        },
        "bounded_adaptive": {
            "answerability_accuracy": 1.0,
            "unsupported_refusal_rate": 1.0,
        },
        "summary": {
            "bounded_adaptive_false_refusal_count": 0,
            "bounded_adaptive_unsupported_generation_count": 0,
            "adaptive_recovery_trigger_count": 3,
        },
    }

    report = render_markdown(baseline, scope_guard)

    assert "Baseline v0.2.1" in report
    assert "Scope guard v0.3.0" in report
    assert "Bounded adaptive" in report
    assert "100.00%" in report
    assert "Decision rule" in report
