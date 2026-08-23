#!/usr/bin/env python3
"""Freeze measured GRPO ablation metrics, hashes, and a Markdown report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from aeroragx.evaluation.grpo_ablation import (
    PolicyAblationResult,
    PolicyEvaluationObservation,
    build_ablation,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> list[PolicyEvaluationObservation]:
    return [
        PolicyEvaluationObservation.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_evidence_metadata(observations: list[PolicyEvaluationObservation]) -> None:
    """Require reproducibility metadata before labeling an ablation measured."""

    for item in observations:
        missing = [
            name for name in ("model_id", "model_revision", "seed") if getattr(item, name) is None
        ]
        if item.variant != "base" and item.adapter_sha256 is None:
            missing.append("adapter_sha256")
        if missing:
            raise ValueError(
                f"Observation {item.variant}/{item.case_id} lacks evidence metadata: {missing}"
            )


def render_report(
    result: PolicyAblationResult,
    observations_sha256: str,
    *,
    synthetic: bool = False,
) -> str:
    rows = [
        ("Task success", "task_success_rate"),
        ("Refusal accuracy", "refusal_accuracy"),
        ("Citation validity", "citation_validity_rate"),
        ("Evidence support", "evidence_support_rate"),
        ("Tool-selection accuracy", "tool_selection_accuracy"),
        ("Structured-output validity", "structured_output_rate"),
        ("Mean tool calls", "mean_tool_calls"),
        ("p50 latency (ms)", "p50_latency_ms"),
        ("p95 latency (ms)", "p95_latency_ms"),
    ]
    lines = [
        "# Base vs LoRA/SFT vs GRPO held-out ablation v0.1",
        "",
        (
            "Status: **synthetic pipeline fixture — not a performance result**"
            if synthetic
            else "Status: **measured from frozen observations**"
        ),
        "",
        f"Observation SHA-256: `{observations_sha256}`",
        "",
        "| Metric | Base | LoRA/SFT | GRPO |",
        "|---|---:|---:|---:|",
    ]
    for label, field in rows:
        values = [
            getattr(result.base, field),
            getattr(result.lora_sft, field),
            getattr(result.grpo, field),
        ]
        lines.append(f"| {label} | {values[0]:.4f} | {values[1]:.4f} | {values[2]:.4f} |")
    lines.extend(
        [
            "",
            "These results use identical protected case IDs for all variants. Report regressions",
            "alongside improvements and retain the model, adapter, seed, data, and receipt hashes.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("observations", type=Path)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("artifacts/evaluation/grpo_agent_ablation_v0_1.json"),
    )
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Exercise report generation with an explicitly labeled .template fixture.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("reports/grpo_agent_ablation_v0_1.measured.md"),
    )
    args = parser.parse_args()

    synthetic = ".template." in args.observations.name
    if synthetic and not args.allow_synthetic:
        raise ValueError("Template observations require --allow-synthetic and are not evidence.")
    observations = load(args.observations)
    validate_evidence_metadata(observations)
    result = build_ablation(observations)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.report_output.write_text(
        render_report(result, sha256(args.observations), synthetic=synthetic),
        encoding="utf-8",
    )
    print(args.json_output)
    print(args.report_output)


if __name__ == "__main__":
    main()
