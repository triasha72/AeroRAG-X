#!/usr/bin/env python3
"""Compare two generation reports only where both conditions are observable."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import statistics
from pathlib import Path
from typing import Any, TypedDict


class PairRow(TypedDict):
    query_id: str
    base_output_tokens: int
    treatment_output_tokens: int
    output_token_delta: int
    base_claim_count: int
    treatment_claim_count: int
    claim_count_delta: int
    base_answer_repeated_word_fraction: float
    treatment_answer_repeated_word_fraction: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-report", type=Path, required=True)
    parser.add_argument("--base-telemetry", type=Path, required=True)
    parser.add_argument("--treatment-report", type=Path, required=True)
    parser.add_argument("--treatment-telemetry", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    return parser.parse_args()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed = {str(row["query_id"]): row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate query IDs prevent paired analysis.")
    return indexed


def _repeated_word_fraction(answer: str) -> float:
    words = re.findall(r"[a-z0-9]+", answer.casefold())
    if not words:
        return 0.0
    return 1.0 - (len(set(words)) / len(words))


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _mean_or_none(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _bootstrap_mean_interval(values: list[float], samples: int) -> tuple[float, float]:
    if not values or samples < 1:
        raise ValueError("Bootstrap analysis requires values and at least one sample.")
    rng = random.Random(20260901)
    means = [statistics.fmean(rng.choice(values) for _ in values) for _ in range(samples)]
    return _percentile(means, 0.025), _percentile(means, 0.975)


def main() -> None:
    args = parse_args()
    base_report = _load(args.base_report)
    treatment_report = _load(args.treatment_report)
    base_telemetry = _load(args.base_telemetry)
    treatment_telemetry = _load(args.treatment_telemetry)

    base_results = _rows_by_id(base_report["query_results"])
    treatment_results = _rows_by_id(treatment_report["query_results"])
    if set(base_results) != set(treatment_results):
        raise ValueError("The reports do not contain the same frozen query IDs.")

    base_usage = _rows_by_id(base_telemetry["query_telemetry"])
    treatment_usage = _rows_by_id(treatment_telemetry["query_telemetry"])
    if set(base_usage) != set(base_results) or set(treatment_usage) != set(base_results):
        raise ValueError("Telemetry is not aligned to the generation reports.")

    completed_ids = sorted(
        query_id
        for query_id in base_results
        if not base_results[query_id]["generation_failed"]
        and not treatment_results[query_id]["generation_failed"]
    )
    provider_ids = [
        query_id
        for query_id in completed_ids
        if base_usage[query_id].get("output_tokens") is not None
        and treatment_usage[query_id].get("output_tokens") is not None
    ]

    pairs: list[PairRow] = []
    for query_id in provider_ids:
        base_output = int(base_usage[query_id]["output_tokens"])
        treatment_output = int(treatment_usage[query_id]["output_tokens"])
        base_answer = str(base_results[query_id]["answer"] or "")
        treatment_answer = str(treatment_results[query_id]["answer"] or "")
        pairs.append(
            {
                "query_id": query_id,
                "base_output_tokens": base_output,
                "treatment_output_tokens": treatment_output,
                "output_token_delta": treatment_output - base_output,
                "base_claim_count": int(base_results[query_id]["claim_count"]),
                "treatment_claim_count": int(treatment_results[query_id]["claim_count"]),
                "claim_count_delta": int(treatment_results[query_id]["claim_count"])
                - int(base_results[query_id]["claim_count"]),
                "base_answer_repeated_word_fraction": _repeated_word_fraction(base_answer),
                "treatment_answer_repeated_word_fraction": _repeated_word_fraction(
                    treatment_answer
                ),
            }
        )

    token_deltas = [float(row["output_token_delta"]) for row in pairs]
    base_tokens = [float(row["base_output_tokens"]) for row in pairs]
    treatment_tokens = [float(row["treatment_output_tokens"]) for row in pairs]
    base_mean = _mean_or_none(base_tokens)
    treatment_mean = _mean_or_none(treatment_tokens)
    mean_delta = _mean_or_none(token_deltas)
    base_claim_mean = _mean_or_none([float(row["base_claim_count"]) for row in pairs])
    treatment_claim_mean = _mean_or_none([float(row["treatment_claim_count"]) for row in pairs])
    base_repeat_mean = _mean_or_none([row["base_answer_repeated_word_fraction"] for row in pairs])
    treatment_repeat_mean = _mean_or_none(
        [row["treatment_answer_repeated_word_fraction"] for row in pairs]
    )
    interval = (
        _bootstrap_mean_interval(token_deltas, args.bootstrap_samples) if token_deltas else None
    )
    delta_sd = statistics.stdev(token_deltas) if len(token_deltas) > 1 else 0.0
    effect_size = mean_delta / delta_sd if mean_delta is not None and delta_sd else None
    relative_change = (
        (treatment_mean - base_mean) / base_mean
        if base_mean is not None and treatment_mean is not None and base_mean != 0.0
        else None
    )
    summary: dict[str, Any] = {
        "version": "0.1",
        "status": "completed" if pairs else "insufficient_paired_observations",
        "frozen_query_count": len(base_results),
        "paired_completed_query_count": len(completed_ids),
        "paired_provider_call_count": len(provider_ids),
        "base_mean_output_tokens": base_mean,
        "treatment_mean_output_tokens": treatment_mean,
        "mean_paired_output_token_delta": mean_delta,
        "mean_paired_output_token_delta_bootstrap_95_ci": (
            list(interval) if interval is not None else None
        ),
        "paired_effect_size_cohen_dz": effect_size,
        "bootstrap_samples": args.bootstrap_samples if pairs else 0,
        "bootstrap_seed": 20260901,
        "relative_output_token_change": relative_change,
        "treatment_lower_token_query_count": sum(row["output_token_delta"] < 0 for row in pairs),
        "equal_token_query_count": sum(row["output_token_delta"] == 0 for row in pairs),
        "treatment_higher_token_query_count": sum(row["output_token_delta"] > 0 for row in pairs),
        "base_mean_claim_count": base_claim_mean,
        "treatment_mean_claim_count": treatment_claim_mean,
        "base_mean_answer_repeated_word_fraction": base_repeat_mean,
        "treatment_mean_answer_repeated_word_fraction": treatment_repeat_mean,
        "inputs": {
            "base_report": str(args.base_report),
            "base_report_sha256": _sha256(args.base_report),
            "base_telemetry_sha256": _sha256(args.base_telemetry),
            "treatment_report": str(args.treatment_report),
            "treatment_report_sha256": _sha256(args.treatment_report),
            "treatment_telemetry_sha256": _sha256(args.treatment_telemetry),
        },
        "query_pairs": pairs,
    }

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Paired generation-efficiency analysis",
        "",
        "Only queries with successful, token-observed provider calls in both conditions "
        "are compared.",
        "Refusals and failures are not silently converted into zero-token observations.",
        "",
        f"Paired completed queries: **{len(completed_ids)}**. "
        f"Paired provider calls: **{len(provider_ids)}**.",
    ]
    if pairs and interval is not None:
        assert base_mean is not None
        assert treatment_mean is not None
        assert mean_delta is not None
        assert base_claim_mean is not None
        assert treatment_claim_mean is not None
        assert base_repeat_mean is not None
        assert treatment_repeat_mean is not None
        assert relative_change is not None
        delta_lower, delta_upper = interval
        lines.extend(
            [
                "",
                "| Metric | Base | Treatment |",
                "|---|---:|---:|",
                f"| Mean output tokens | {base_mean:.2f} | {treatment_mean:.2f} |",
                f"| Mean claims | {base_claim_mean:.2f} | {treatment_claim_mean:.2f} |",
                "| Mean repeated-word fraction | "
                f"{base_repeat_mean:.4f} | {treatment_repeat_mean:.4f} |",
                "",
                f"Mean treatment-minus-Base output delta: **{mean_delta:+.2f} tokens**.",
                f"Paired bootstrap 95% interval: **[{delta_lower:+.2f}, {delta_upper:+.2f}] "
                f"tokens** ({args.bootstrap_samples:,} deterministic resamples).",
                f"Paired effect size (Cohen's dz): **{float(effect_size or 0.0):+.3f}**.",
                f"Relative treatment output change: **{relative_change:+.2%}**.",
                "Treatment used fewer/equal/more tokens on "
                f"**{summary['treatment_lower_token_query_count']} / "
                f"{summary['equal_token_query_count']} / "
                f"{summary['treatment_higher_token_query_count']}** paired calls.",
                "",
                "This is a descriptive paired analysis of the frozen sample, not a "
                "population-level significance claim.",
            ]
        )
    else:
        lines.extend(
            [
                "No query had successful, token-observed provider calls in both conditions.",
                "No means, confidence interval, effect size, or relative token claim is made.",
            ]
        )
    args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        json.dumps({key: value for key, value in summary.items() if key != "query_pairs"}, indent=2)
    )


if __name__ == "__main__":
    main()
