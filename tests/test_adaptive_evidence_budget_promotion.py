"""Tests for fail-closed adaptive-policy promotion."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_adaptive_evidence_budget_promotion.py"


def _run(tmp_path: Path, *, expanded: int, effective: int, recovered: bool = True):
    quality = tmp_path / "quality.json"
    budget = tmp_path / "budget.json"
    paired = tmp_path / "paired.json"
    output = tmp_path / "output.json"
    quality.write_text('{"status":"promoted"}\n')
    decisions = [{"expanded": True, "maximum_sufficient": recovered} for _ in range(expanded)]
    budget.write_text(
        json.dumps(
            {
                "expanded_count": expanded,
                "retained_top3_count": 50 - expanded,
                "decisions": decisions,
            }
        )
    )
    paired.write_text(json.dumps({"treatment_higher_token_query_count": effective}))
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--quality-decision",
            str(quality),
            "--budget-decisions",
            str(budget),
            "--adaptive-vs-top3",
            str(paired),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result, json.loads(output.read_text())


def test_mixed_effective_policy_passes(tmp_path: Path) -> None:
    result, decision = _run(tmp_path, expanded=4, effective=4)
    assert result.returncode == 0
    assert decision["status"] == "promoted"


def test_noop_policy_is_rejected(tmp_path: Path) -> None:
    result, decision = _run(tmp_path, expanded=1, effective=0)
    assert result.returncode != 0
    assert decision["status"] == "rejected"


def test_expansion_without_recovered_sufficiency_is_rejected(tmp_path: Path) -> None:
    result, decision = _run(tmp_path, expanded=4, effective=4, recovered=False)
    assert result.returncode != 0
    assert decision["checks"]["all_expansions_recover_sufficiency"] is False
