"""Tests for deterministic release-readiness evidence checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aeroragx.release import (
    build_readiness_report,
    load_readiness_policy,
)


def test_readiness_report_passes_with_required_and_frozen_evidence(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"status": "frozen"}\n', encoding="utf-8")
    checksum = hashlib.sha256(evidence.read_bytes()).hexdigest()

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "frozen_inputs": [
                    {
                        "path": "evidence.json",
                        "sha256": checksum,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    required = tmp_path / "report.md"
    required.write_text("# report\n", encoding="utf-8")

    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                'version: "test"',
                'baseline_manifest: "manifest.json"',
                "required_files:",
                '  - "report.md"',
            ]
        ),
        encoding="utf-8",
    )

    report = build_readiness_report(
        project_root=tmp_path,
        policy=load_readiness_policy(policy_path),
    )

    assert report.passed is True
    assert all(check.passed for check in report.checks)
    assert "**Result:** PASS" in report.to_markdown()


def test_readiness_report_fails_for_checksum_drift(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"status": "changed"}\n', encoding="utf-8")

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "frozen_inputs": [
                    {
                        "path": "evidence.json",
                        "sha256": "0" * 64,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        "\n".join(
            [
                'version: "test"',
                'baseline_manifest: "manifest.json"',
                "required_files: []",
            ]
        ),
        encoding="utf-8",
    )

    report = build_readiness_report(
        project_root=tmp_path,
        policy=load_readiness_policy(policy_path),
    )

    assert report.passed is False
    assert "mismatch: evidence.json" in report.checks[-1].detail
