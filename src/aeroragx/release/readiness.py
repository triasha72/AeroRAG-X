"""Deterministic release-readiness checks over committed project evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class ReadinessPolicy:
    """Versioned inputs required for one release-readiness decision."""

    version: str
    baseline_manifest: Path
    required_files: tuple[Path, ...]
    forbidden_markers: dict[Path, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """One machine-readable readiness check."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Aggregate release-readiness result."""

    policy_version: str
    passed: bool
    checks: tuple[ReadinessCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible representation."""

        return {
            "policy_version": self.policy_version,
            "passed": self.passed,
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "detail": check.detail,
                }
                for check in self.checks
            ],
        }

    def to_markdown(self) -> str:
        """Return a compact human-readable report."""

        status = "PASS" if self.passed else "FAIL"
        lines = [
            "# AeroRAG-X release readiness",
            "",
            f"**Policy:** {self.policy_version}  ",
            f"**Result:** {status}",
            "",
            "## Checks",
            "",
        ]

        for check in self.checks:
            marker = "x" if check.passed else " "
            lines.append(f"- [{marker}] **{check.name}** — {check.detail}")

        lines.append("")

        return "\n".join(lines)


def load_readiness_policy(
    path: Path,
) -> ReadinessPolicy:
    """Load and validate one YAML readiness policy."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Readiness policy must be a mapping.")

    version = payload.get("version")
    baseline_manifest = payload.get("baseline_manifest")
    required_files = payload.get("required_files")
    forbidden_markers = payload.get("forbidden_markers", {})

    if not isinstance(version, str) or not version:
        raise ValueError("Readiness policy version must be a non-empty string.")

    if not isinstance(baseline_manifest, str) or not baseline_manifest:
        raise ValueError("Readiness policy baseline_manifest must be a path.")

    if not isinstance(required_files, list) or not all(
        isinstance(item, str) and item for item in required_files
    ):
        raise ValueError("Readiness policy required_files must be a list of paths.")

    if not isinstance(forbidden_markers, dict) or not all(
        isinstance(raw_path, str)
        and raw_path
        and isinstance(markers, list)
        and markers
        and all(isinstance(marker, str) and marker for marker in markers)
        for raw_path, markers in forbidden_markers.items()
    ):
        raise ValueError(
            "Readiness policy forbidden_markers must map paths to non-empty string lists."
        )

    return ReadinessPolicy(
        version=version,
        baseline_manifest=Path(baseline_manifest),
        required_files=tuple(Path(item) for item in required_files),
        forbidden_markers={
            Path(raw_path): tuple(markers) for raw_path, markers in forbidden_markers.items()
        },
    )


def _sha256(
    path: Path,
) -> str:
    """Return the SHA-256 checksum for one file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_readiness_report(
    *,
    project_root: Path,
    policy: ReadinessPolicy,
) -> ReadinessReport:
    """Check required evidence and frozen baseline integrity."""

    checks: list[ReadinessCheck] = []

    for relative_path in policy.required_files:
        path = project_root / relative_path
        exists = path.is_file() and path.stat().st_size > 0
        checks.append(
            ReadinessCheck(
                name=f"required:{relative_path}",
                passed=exists,
                detail=("present and non-empty" if exists else "missing or empty"),
            )
        )

    for relative_path, markers in policy.forbidden_markers.items():
        path = project_root / relative_path
        if not path.is_file():
            checks.append(
                ReadinessCheck(
                    name=f"finalized:{relative_path}",
                    passed=False,
                    detail="missing evidence file",
                )
            )
            continue

        contents = path.read_text(encoding="utf-8").casefold()
        found = sorted(marker for marker in markers if marker.casefold() in contents)
        checks.append(
            ReadinessCheck(
                name=f"finalized:{relative_path}",
                passed=not found,
                detail=(
                    "contains no forbidden placeholders"
                    if not found
                    else f"placeholder markers found: {', '.join(found)}"
                ),
            )
        )

    manifest_path = project_root / policy.baseline_manifest

    if not manifest_path.is_file():
        checks.append(
            ReadinessCheck(
                name="frozen-baseline-manifest",
                passed=False,
                detail=f"missing: {policy.baseline_manifest}",
            )
        )
    else:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        frozen_inputs = payload.get("frozen_inputs")

        if not isinstance(frozen_inputs, list):
            checks.append(
                ReadinessCheck(
                    name="frozen-baseline-manifest",
                    passed=False,
                    detail="frozen_inputs is missing or invalid",
                )
            )
        else:
            mismatches: list[str] = []

            for item in frozen_inputs:
                if not isinstance(item, dict):
                    mismatches.append("<invalid manifest item>")
                    continue

                raw_path = item.get("path")
                expected = item.get("sha256")

                if not isinstance(raw_path, str) or not isinstance(expected, str):
                    mismatches.append("<invalid manifest fields>")
                    continue

                path = project_root / raw_path

                if not path.is_file() or _sha256(path) != expected:
                    mismatches.append(raw_path)

            checks.append(
                ReadinessCheck(
                    name="frozen-baseline-checksums",
                    passed=not mismatches,
                    detail=(
                        f"verified {len(frozen_inputs)} frozen inputs"
                        if not mismatches
                        else f"mismatch: {', '.join(mismatches)}"
                    ),
                )
            )

    return ReadinessReport(
        policy_version=policy.version,
        passed=all(check.passed for check in checks),
        checks=tuple(checks),
    )
