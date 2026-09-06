#!/usr/bin/env python3
"""Build and verify the 50-case context-compaction development benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / "data/evaluation/generation_queries_compact_dev_v0_1.jsonl"
SCOPE = ROOT / "data/evaluation/adaptive_scope_challenge_v0_1.jsonl"
SOURCE = ROOT / "data/evaluation/source_grounded_queries_v0_1_512.jsonl"
PROTECTED = (
    ROOT / "data/evaluation/generation_queries_v0_3.jsonl",
    ROOT / "data/evaluation/generation_queries_v0_4_heldout.jsonl",
    ROOT / "data/evaluation/scope_qualifier_heldout_v0_1.jsonl",
)
DEFAULT_OUTPUT = ROOT / "data/evaluation/generation_queries_context_dev_v0_2.jsonl"
DEFAULT_MANIFEST = ROOT / "data/evaluation/generation_queries_context_dev_v0_2_manifest.json"


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> tuple[bytes, bytes]:
    protected_rows = [row for path in PROTECTED for row in _rows(path)]
    protected_ids = {str(row["query_id"]) for row in protected_rows}
    protected_text = {_normalized(str(row["query"])) for row in protected_rows}

    selected: list[dict[str, Any]] = []
    selected_text: set[str] = set()
    source_counts = {"curated_compact": 0, "scope_challenge": 0, "automatic_source_stress": 0}

    def add(row: dict[str, Any], source_kind: str) -> bool:
        query_id = str(row["query_id"])
        query = str(row["query"])
        normalized = _normalized(query)
        if query_id in protected_ids or normalized in protected_text or normalized in selected_text:
            return False
        selected.append(
            {
                "query_id": query_id,
                "query": query,
                "expected_answerable": bool(row["expected_answerable"]),
                "expected_terms": list(row.get("expected_terms", [])),
            }
        )
        selected_text.add(normalized)
        source_counts[source_kind] += 1
        return True

    for row in _rows(CURATED):
        add(row, "curated_compact")
    for row in _rows(SCOPE):
        if not bool(row["expected_answerable"]):
            add(row, "scope_challenge")
    for row in _rows(SOURCE):
        candidate = {**row, "expected_answerable": True}
        add(candidate, "automatic_source_stress")
        if source_counts["automatic_source_stress"] == 32:
            break

    if source_counts != {
        "curated_compact": 8,
        "scope_challenge": 10,
        "automatic_source_stress": 32,
    }:
        raise ValueError(f"Unexpected source composition: {source_counts}")
    if len(selected) != 50:
        raise ValueError(f"Expected 50 development cases, found {len(selected)}")

    output_bytes = b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in selected
    )
    manifest = {
        "version": "0.2",
        "status": "development_only",
        "allowed_claim": "context-compaction development and robustness diagnostic",
        "prohibited_claim": "independently human-validated or protected generation quality",
        "query_count": len(selected),
        "answerable_count": sum(bool(row["expected_answerable"]) for row in selected),
        "unsupported_count": sum(not bool(row["expected_answerable"]) for row in selected),
        "source_counts": source_counts,
        "selection": (
            "all curated compact; all unique unsupported scope; first 32 unique source candidates"
        ),
        "normalization": "casefold and replace non-alphanumeric runs with one space",
        "protected_overlap_count": 0,
        "inputs": {
            str(path.relative_to(ROOT)): _sha256(path.read_bytes())
            for path in (CURATED, SCOPE, SOURCE, *PROTECTED)
        },
        "output_sha256": _sha256(output_bytes),
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return output_bytes, manifest_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output_bytes, manifest_bytes = build()
    if args.check:
        if args.output.read_bytes() != output_bytes or args.manifest.read_bytes() != manifest_bytes:
            raise SystemExit("Development dataset or manifest differs from deterministic build.")
        print("Context-compaction development dataset and manifest verified.")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output_bytes)
    args.manifest.write_bytes(manifest_bytes)
    print(f"Wrote 50 development cases to {args.output}")


if __name__ == "__main__":
    main()
