#!/usr/bin/env python3
"""Build the consolidated Phase 24 quality report from frozen evaluation summaries."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "artifacts" / "evaluation"
REPORTS = ROOT / "reports"

SEMANTIC_PATH = EVAL / "semantic_four_way_coverage_v0_1.json"
CLAIM_SUPPORT_PATH = EVAL / "claim_support_summary_v0_1.json"
COMPLETENESS_PATH = EVAL / "answer_claim_completeness_summary_v0_1.json"
REDUNDANCY_PATH = EVAL / "claim_redundancy_summary_v0_1.json"
UNSUPPORTED_PATH = EVAL / "unsupported_response_taxonomy_summary_v0_1.json"

SUMMARY_PATH = EVAL / "phase24_quality_summary_v0_1.json"
REPORT_PATH = REPORTS / "phase24_quality_v0_1.md"

EXPECTED = {
    "semantic_base_lower": 0.3815789473684211,
    "semantic_base_upper": 0.5394736842105263,
    "semantic_lora_lower": 0.5131578947368421,
    "semantic_lora_upper": 0.6578947368421053,
    "claim_support_base_strict": 0.65625,
    "claim_support_lora_strict": 0.679245,
    "claim_support_base_broad": 0.875,
    "claim_support_lora_broad": 0.90566,
    "completeness_base_full": 0.1,
    "completeness_lora_full": 0.45,
    "completeness_base_broad": 0.6,
    "completeness_lora_broad": 0.95,
    "redundancy_base": 0.0,
    "redundancy_lora": 0.018868,
    "overlap_base": 0.125,
    "overlap_lora": 0.396226,
    "unsupported_base_closed_safe": 0.583333,
    "unsupported_lora_closed_safe": 0.75,
    "unsupported_base_rag_safe": 1.0,
    "unsupported_lora_rag_safe": 1.0,
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required frozen input is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path}: expected JSON object")
    return value


def assert_close(name: str, observed: float, expected: float) -> None:
    if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(f"{name}: observed {observed!r}, expected {expected!r}")


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def signed_pp(value: float) -> str:
    return f"{100.0 * value:+.2f} pp"


def main() -> None:
    semantic = load_json(SEMANTIC_PATH)
    claim_support = load_json(CLAIM_SUPPORT_PATH)
    completeness = load_json(COMPLETENESS_PATH)
    redundancy = load_json(REDUNDANCY_PATH)
    unsupported = load_json(UNSUPPORTED_PATH)

    sem = semantic["systems"]
    cs = claim_support["systems"]
    comp = completeness["systems"]
    red = redundancy["systems"]
    uns = unsupported["conditions"]

    base = {
        "semantic_lower": float(sem["base_rag"]["micro_coverage_lower_bound"]),
        "semantic_upper": float(sem["base_rag"]["micro_coverage_upper_bound"]),
        "claim_support_strict": float(cs["base_rag"]["strict_support_rate"]),
        "claim_support_broad": float(cs["base_rag"]["support_or_partial_rate"]),
        "claim_count": int(cs["base_rag"]["total_claims"]),
        "contradicted_claims": int(cs["base_rag"]["contradicted"]),
        "completeness_full": float(comp["base_rag"]["full_capture_rate"]),
        "completeness_broad": float(comp["base_rag"]["full_or_partial_capture_rate"]),
        "redundancy_rate": float(red["base_rag"]["redundancy_rate"]),
        "overlap_rate": float(red["base_rag"]["overlap_rate"]),
        "nonredundant_rate": float(red["base_rag"]["nonredundant_rate"]),
        "unsupported_safe": float(uns["base_rag"]["safe_non_assertion_rate"]),
        "unsupported_assertion_rate": float(uns["base_rag"]["unsupported_assertion_rate"]),
    }

    lora = {
        "semantic_lower": float(sem["lora_rag"]["micro_coverage_lower_bound"]),
        "semantic_upper": float(sem["lora_rag"]["micro_coverage_upper_bound"]),
        "claim_support_strict": float(cs["lora_rag"]["strict_support_rate"]),
        "claim_support_broad": float(cs["lora_rag"]["support_or_partial_rate"]),
        "claim_count": int(cs["lora_rag"]["total_claims"]),
        "contradicted_claims": int(cs["lora_rag"]["contradicted"]),
        "completeness_full": float(comp["lora_rag"]["full_capture_rate"]),
        "completeness_broad": float(comp["lora_rag"]["full_or_partial_capture_rate"]),
        "redundancy_rate": float(red["lora_rag"]["redundancy_rate"]),
        "overlap_rate": float(red["lora_rag"]["overlap_rate"]),
        "nonredundant_rate": float(red["lora_rag"]["nonredundant_rate"]),
        "unsupported_safe": float(uns["lora_rag"]["safe_non_assertion_rate"]),
        "unsupported_assertion_rate": float(uns["lora_rag"]["unsupported_assertion_rate"]),
    }

    observed_checks = {
        "semantic_base_lower": base["semantic_lower"],
        "semantic_base_upper": base["semantic_upper"],
        "semantic_lora_lower": lora["semantic_lower"],
        "semantic_lora_upper": lora["semantic_upper"],
        "claim_support_base_strict": base["claim_support_strict"],
        "claim_support_lora_strict": lora["claim_support_strict"],
        "claim_support_base_broad": base["claim_support_broad"],
        "claim_support_lora_broad": lora["claim_support_broad"],
        "completeness_base_full": base["completeness_full"],
        "completeness_lora_full": lora["completeness_full"],
        "completeness_base_broad": base["completeness_broad"],
        "completeness_lora_broad": lora["completeness_broad"],
        "redundancy_base": base["redundancy_rate"],
        "redundancy_lora": lora["redundancy_rate"],
        "overlap_base": base["overlap_rate"],
        "overlap_lora": lora["overlap_rate"],
        "unsupported_base_closed_safe": float(uns["base_closed_book"]["safe_non_assertion_rate"]),
        "unsupported_lora_closed_safe": float(uns["lora_closed_book"]["safe_non_assertion_rate"]),
        "unsupported_base_rag_safe": base["unsupported_safe"],
        "unsupported_lora_rag_safe": lora["unsupported_safe"],
    }

    for name, expected in EXPECTED.items():
        assert_close(name, observed_checks[name], expected)

    deltas = {
        "semantic_lower": round(lora["semantic_lower"] - base["semantic_lower"], 6),
        "semantic_upper": round(lora["semantic_upper"] - base["semantic_upper"], 6),
        "claim_support_strict": round(
            lora["claim_support_strict"] - base["claim_support_strict"], 6
        ),
        "claim_support_broad": round(lora["claim_support_broad"] - base["claim_support_broad"], 6),
        "completeness_full": round(lora["completeness_full"] - base["completeness_full"], 6),
        "completeness_broad": round(lora["completeness_broad"] - base["completeness_broad"], 6),
        "redundancy_rate": round(lora["redundancy_rate"] - base["redundancy_rate"], 6),
        "overlap_rate": round(lora["overlap_rate"] - base["overlap_rate"], 6),
        "unsupported_safe": round(lora["unsupported_safe"] - base["unsupported_safe"], 6),
    }

    closed_book = {
        "base_safe_non_assertion_rate": float(uns["base_closed_book"]["safe_non_assertion_rate"]),
        "lora_safe_non_assertion_rate": float(uns["lora_closed_book"]["safe_non_assertion_rate"]),
        "base_unsupported_assertion_rate": float(
            uns["base_closed_book"]["unsupported_assertion_rate"]
        ),
        "lora_unsupported_assertion_rate": float(
            uns["lora_closed_book"]["unsupported_assertion_rate"]
        ),
    }

    summary = {
        "version": "v0.1",
        "phase": 24,
        "evaluation": "consolidated_quality",
        "scope": (
            "Consolidation of frozen semantic concept coverage, claim-evidence "
            "support, answer-to-claim completeness, within-answer claim "
            "redundancy, and unsupported-response taxonomy evaluations."
        ),
        "source_files": [
            str(SEMANTIC_PATH.relative_to(ROOT)),
            str(CLAIM_SUPPORT_PATH.relative_to(ROOT)),
            str(COMPLETENESS_PATH.relative_to(ROOT)),
            str(REDUNDANCY_PATH.relative_to(ROOT)),
            str(UNSUPPORTED_PATH.relative_to(ROOT)),
        ],
        "grounded_systems": {
            "base_rag": base,
            "lora_rag": lora,
        },
        "lora_minus_base_grounded": deltas,
        "closed_book_unsupported_behavior": closed_book,
        "guardrails": [
            "Metrics measure different properties and must not be collapsed "
            "into a single accuracy score.",
            "Expected-concept coverage is a protected benchmark result, not "
            "universal factual correctness.",
            "Claim support measures support from cited evidence, not universal truth.",
            "Completeness measures representation of prose content in formal "
            "claims, not evidence support.",
            "OVERLAPPING claims are not counted as fully redundant.",
            "UNSUPPORTED_ASSERTION is defined relative to the frozen benchmark contract.",
            "The adjudication stages are single structured passes, not "
            "independent multi-assessor studies.",
            "No generation, retrieval, training, or model-selection run is "
            "repeated by this consolidation.",
        ],
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    REPORTS.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Phase 24 consolidated quality evaluation v0.1",
        "",
        "## Scope",
        "",
        (
            "This report consolidates the frozen Phase 24 quality evaluations "
            "without rerunning generation, retrieval, training, or model selection."
        ),
        "",
        "The component evaluations measure different properties:",
        "",
        "- semantic expected-concept coverage;",
        "- claim-to-cited-evidence support;",
        "- answer-to-formal-claim completeness;",
        "- within-answer claim redundancy/overlap;",
        "- unsupported-query response behavior.",
        "",
        "They are intentionally reported separately rather than collapsed into a single score.",
        "",
        "## Grounded-system comparison",
        "",
        "| Dimension | Base + RAG | LoRA + RAG | LoRA - Base |",
        "|---|---:|---:|---:|",
        (
            f"| Semantic concept coverage, conservative micro | "
            f"{pct(base['semantic_lower'])} | {pct(lora['semantic_lower'])} | "
            f"{signed_pp(deltas['semantic_lower'])} |"
        ),
        (
            f"| Semantic concept coverage, upper-bound micro | "
            f"{pct(base['semantic_upper'])} | {pct(lora['semantic_upper'])} | "
            f"{signed_pp(deltas['semantic_upper'])} |"
        ),
        (
            f"| Strict claim-evidence support | "
            f"{pct(base['claim_support_strict'])} | {pct(lora['claim_support_strict'])} | "
            f"{signed_pp(deltas['claim_support_strict'])} |"
        ),
        (
            f"| Support-or-partial claim-evidence support | "
            f"{pct(base['claim_support_broad'])} | {pct(lora['claim_support_broad'])} | "
            f"{signed_pp(deltas['claim_support_broad'])} |"
        ),
        (
            f"| Full answer-to-claim capture | "
            f"{pct(base['completeness_full'])} | {pct(lora['completeness_full'])} | "
            f"{signed_pp(deltas['completeness_full'])} |"
        ),
        (
            f"| Full-or-partial answer-to-claim capture | "
            f"{pct(base['completeness_broad'])} | {pct(lora['completeness_broad'])} | "
            f"{signed_pp(deltas['completeness_broad'])} |"
        ),
        (
            f"| Full redundancy rate | "
            f"{pct(base['redundancy_rate'])} | {pct(lora['redundancy_rate'])} | "
            f"{signed_pp(deltas['redundancy_rate'])} |"
        ),
        (
            f"| Partial-overlap rate | "
            f"{pct(base['overlap_rate'])} | {pct(lora['overlap_rate'])} | "
            f"{signed_pp(deltas['overlap_rate'])} |"
        ),
        (
            f"| Unsupported-query safe non-assertion | "
            f"{pct(base['unsupported_safe'])} | {pct(lora['unsupported_safe'])} | "
            f"{signed_pp(deltas['unsupported_safe'])} |"
        ),
        "",
        "## Claim decomposition",
        "",
        f"- Base + RAG produced **{base['claim_count']}** formal claims.",
        f"- LoRA + RAG produced **{lora['claim_count']}** formal claims.",
        (
            f"- Base + RAG had **{base['contradicted_claims']}** contradicted "
            "claim(s) under the frozen claim-support policy."
        ),
        (
            f"- LoRA + RAG had **{lora['contradicted_claims']}** contradicted "
            "claim(s) under the frozen claim-support policy."
        ),
        (
            "- The LoRA condition therefore shows richer formal decomposition, "
            "but the higher claim count is not treated as a quality metric by itself."
        ),
        "",
        "## Unsupported-query behavior",
        "",
        "| Condition | Safe non-assertion | Unsupported-assertion rate |",
        "|---|---:|---:|",
        (
            f"| Base closed-book | "
            f"{pct(closed_book['base_safe_non_assertion_rate'])} | "
            f"{pct(closed_book['base_unsupported_assertion_rate'])} |"
        ),
        (
            f"| LoRA closed-book | "
            f"{pct(closed_book['lora_safe_non_assertion_rate'])} | "
            f"{pct(closed_book['lora_unsupported_assertion_rate'])} |"
        ),
        (
            f"| Base + RAG | {pct(base['unsupported_safe'])} | "
            f"{pct(base['unsupported_assertion_rate'])} |"
        ),
        (
            f"| LoRA + RAG | {pct(lora['unsupported_safe'])} | "
            f"{pct(lora['unsupported_assertion_rate'])} |"
        ),
        "",
        "## Findings",
        "",
        (
            "1. **Semantic coverage:** LoRA + RAG contains more of the predefined "
            "technical concepts than Base + RAG on the protected answerable benchmark."
        ),
        (
            "2. **Evidence support:** claim-to-cited-evidence support rates remain "
            "broadly similar between the two grounded conditions; the LoRA condition "
            "also contains a small number of contradicted claims."
        ),
        (
            "3. **Formal completeness:** LoRA + RAG captures materially more of its "
            "prose-answer content in the formal claim structure."
        ),
        (
            "4. **Redundancy:** the additional LoRA claims are rarely fully redundant, "
            "but partial semantic overlap is substantially higher."
        ),
        (
            "5. **Unsupported-query boundary:** both grounded conditions avoid "
            "unsupported substantive answering on all 12 protected unsupported queries, "
            "while the closed-book conditions do not."
        ),
        "",
        "## Defensible conclusion",
        "",
        (
            "On this protected grounded benchmark, LoRA increased structured technical "
            "decomposition and answer-to-claim completeness, and it produced higher "
            "expected-concept coverage while maintaining broadly similar claim-to-evidence "
            "support rates. The additional claims were rarely fully redundant, although "
            "partial semantic overlap increased substantially and a small number of "
            "contradicted LoRA claims remained. Retrieval-grounded execution provided the "
            "strongest unsupported-query boundary in both grounded conditions."
        ),
        "",
        "## Guardrails",
        "",
        (
            "- These results do not establish universal factual accuracy or universal "
            "model superiority."
        ),
        (
            "- Claim-evidence support, semantic coverage, completeness, redundancy, "
            "and unsupported-query behavior are separate properties."
        ),
        ("- `OVERLAPPING` does not mean fully redundant."),
        ("- `UNSUPPORTED_ASSERTION` is defined relative to the frozen benchmark contract."),
        (
            "- Adjudication results come from single structured passes under frozen "
            "policies, not independent multi-assessor studies."
        ),
        (
            "- No model, retrieval, training, or generation rerun was performed for "
            "this consolidation."
        ),
        "",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("source summaries: 5")
    print("grounded systems: base_rag, lora_rag")
    print(
        "semantic conservative micro:",
        f"{base['semantic_lower']:.6f}",
        f"{lora['semantic_lower']:.6f}",
    )
    print(
        "strict claim support:",
        f"{base['claim_support_strict']:.6f}",
        f"{lora['claim_support_strict']:.6f}",
    )
    print(
        "full answer-to-claim capture:",
        f"{base['completeness_full']:.6f}",
        f"{lora['completeness_full']:.6f}",
    )
    print(
        "full redundancy:",
        f"{base['redundancy_rate']:.6f}",
        f"{lora['redundancy_rate']:.6f}",
    )
    print(
        "grounded unsupported safe behavior:",
        f"{base['unsupported_safe']:.6f}",
        f"{lora['unsupported_safe']:.6f}",
    )
    print("PHASE 24 QUALITY CONSOLIDATION: PASS")
    print("summary:", SUMMARY_PATH)
    print("report:", REPORT_PATH)


if __name__ == "__main__":
    main()
