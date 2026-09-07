#!/usr/bin/env python3
"""Build a development set containing real top-3-to-top-5 recovery opportunities."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from aeroragx.generation.evidence_budget import (
    AdaptiveEvidenceBudgetIndex,
    load_evidence_budget_config,
)
from aeroragx.generation.sufficiency import (
    EvidenceSufficiencyAssessor,
    load_sufficiency_config,
)
from aeroragx.runtime import RuntimeConfig, load_reranker_index

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/evaluation/generation_queries_context_dev_v0_2.jsonl"
SOURCE = ROOT / "data/evaluation/source_grounded_queries_v0_1_512.jsonl"
PROTECTED = (
    ROOT / "data/evaluation/generation_queries_v0_3.jsonl",
    ROOT / "data/evaluation/generation_queries_v0_4_heldout.jsonl",
    ROOT / "data/evaluation/scope_qualifier_heldout_v0_1.jsonl",
)
OUTPUT = ROOT / "data/evaluation/generation_queries_adaptive_dev_v0_1.jsonl"
MANIFEST = ROOT / "data/evaluation/generation_queries_adaptive_dev_v0_1_manifest.json"
DIAGNOSTIC = ROOT / "artifacts/evaluation/adaptive_context_recovery_scan_v0_1.json"


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-recovery-cases", type=int, default=20)
    args = parser.parse_args()

    base = _rows(BASE)
    protected = [row for path in PROTECTED for row in _rows(path)]
    excluded_ids = {row["query_id"] for row in [*base, *protected]}
    excluded_text = {_normalized(row["query"]) for row in [*base, *protected]}

    reranker, _ = load_reranker_index(RuntimeConfig(candidate_top_k=20, evidence_top_k=5))
    assessor = EvidenceSufficiencyAssessor(
        load_sufficiency_config(ROOT / "configs/sufficiency_v0_1.yaml")
    )
    selector = AdaptiveEvidenceBudgetIndex(
        reranker,
        assessor,
        load_evidence_budget_config(ROOT / "configs/evidence_budget_adaptive_3_to_5_v0_1.yaml"),
    )

    selected: list[dict[str, Any]] = []
    selected_decisions: list[dict[str, Any]] = []
    scanned = 0
    for row in _rows(SOURCE):
        query_id = str(row["query_id"])
        query = str(row["query"])
        normalized = _normalized(query)
        if query_id in excluded_ids or normalized in excluded_text:
            continue
        scanned += 1
        selector.search(query, top_k=5)
        decision = selector.decisions[-1]
        if not decision.expanded:
            continue
        selected.append(
            {
                "query_id": query_id,
                "query": query,
                "expected_answerable": True,
                "expected_terms": list(row["expected_terms"]),
            }
        )
        selected_decisions.append(decision.model_dump(mode="json"))
        excluded_ids.add(query_id)
        excluded_text.add(normalized)
        if len(selected) == args.target_recovery_cases:
            break

    diagnostic = {
        "version": "0.1",
        "status": (
            "sufficient_recovery_cases"
            if len(selected) >= args.target_recovery_cases
            else "insufficient_recovery_cases"
        ),
        "target_recovery_case_count": args.target_recovery_cases,
        "found_recovery_case_count": len(selected),
        "source_candidates_scanned": scanned,
        "recovery_query_ids": [row["query_id"] for row in selected],
        "recovery_decisions": selected_decisions,
        "selection_rule": "top-3 insufficient, top-5 sufficient, no unsupported-signal blocker",
    }
    DIAGNOSTIC.parent.mkdir(parents=True, exist_ok=True)
    DIAGNOSTIC.write_text(json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if len(selected) < args.target_recovery_cases:
        raise SystemExit(
            f"Found only {len(selected)} recovery cases after scanning {scanned}; "
            f"required {args.target_recovery_cases}. Diagnostic: {DIAGNOSTIC}"
        )
    combined = [*base, *selected]
    output_bytes = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in combined
    )
    OUTPUT.write_bytes(output_bytes)
    manifest = {
        "version": "0.1",
        "status": "development_only_automatic_recovery_challenge",
        "allowed_claim": "adaptive evidence-budget recovery and token diagnostic",
        "prohibited_claim": "human-validated or protected generation quality",
        "query_count": len(combined),
        "base_query_count": len(base),
        "recovery_case_count": len(selected),
        "source_candidates_scanned": scanned,
        "selection_rule": "top-3 insufficient, top-5 sufficient, no unsupported-signal blocker",
        "recovery_query_ids": [row["query_id"] for row in selected],
        "recovery_decisions": selected_decisions,
        "inputs": {
            str(path.relative_to(ROOT)): _sha(path)
            for path in (
                BASE,
                SOURCE,
                *PROTECTED,
                ROOT / "configs/sufficiency_v0_1.yaml",
                ROOT / "configs/evidence_budget_adaptive_3_to_5_v0_1.yaml",
                ROOT / "data/processed/ntrs/v0_1/chunks.jsonl",
                ROOT / "artifacts/embeddings/ntrs_v0_1.npy",
                ROOT / "artifacts/embeddings/ntrs_v0_1_metadata.jsonl",
                ROOT / "artifacts/embeddings/ntrs_v0_1_manifest.json",
            )
        },
        "output_sha256": hashlib.sha256(output_bytes).hexdigest(),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote {len(combined)} cases ({len(selected)} recovery cases; "
        f"scanned {scanned}) to {OUTPUT}"
    )


if __name__ == "__main__":
    main()
