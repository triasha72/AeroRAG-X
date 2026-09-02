"""Regression tests for paired generation-efficiency analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import analyze_paired_generation_efficiency as analysis


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_zero_paired_calls_write_insufficient_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report = {
        "query_results": [
            {
                "query_id": "q1",
                "generation_failed": True,
                "answer": "",
                "claim_count": 0,
            }
        ]
    }
    telemetry = {
        "query_telemetry": [
            {
                "query_id": "q1",
                "output_tokens": None,
            }
        ]
    }
    paths = {
        name: tmp_path / name
        for name in (
            "base.json",
            "base-telemetry.json",
            "treatment.json",
            "treatment-telemetry.json",
            "summary.json",
            "summary.md",
        )
    }
    _write(paths["base.json"], report)
    _write(paths["treatment.json"], report)
    _write(paths["base-telemetry.json"], telemetry)
    _write(paths["treatment-telemetry.json"], telemetry)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "analyze",
            "--base-report",
            str(paths["base.json"]),
            "--base-telemetry",
            str(paths["base-telemetry.json"]),
            "--treatment-report",
            str(paths["treatment.json"]),
            "--treatment-telemetry",
            str(paths["treatment-telemetry.json"]),
            "--json-output",
            str(paths["summary.json"]),
            "--markdown-output",
            str(paths["summary.md"]),
        ],
    )

    analysis.main()

    summary = json.loads(paths["summary.json"].read_text(encoding="utf-8"))
    assert summary["status"] == "insufficient_paired_observations"
    assert summary["paired_provider_call_count"] == 0
    assert summary["base_mean_output_tokens"] is None
    assert summary["treatment_mean_output_tokens"] is None
    assert summary["mean_paired_output_token_delta"] is None
    assert summary["mean_paired_output_token_delta_bootstrap_95_ci"] is None
    assert summary["relative_output_token_change"] is None
    assert "No query had successful" in paths["summary.md"].read_text(encoding="utf-8")
