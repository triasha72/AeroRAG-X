#!/usr/bin/env python3
"""Create a comparable retrieval-method receipt from frozen metric artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

METRICS = ("recall_at_5", "recall_at_10", "mrr_at_10", "ndcg_at_10")


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = ("model_name", "query_count", *METRICS)
    missing = [metric for metric in required if metric not in payload]
    if missing:
        raise ValueError(f"{path} is not a retrieval metric artifact; missing {missing}")
    return payload


def summarize(paths: list[Path]) -> dict[str, object]:
    artifacts = [(path, load(path)) for path in paths]
    counts = {int(payload["query_count"]) for _, payload in artifacts}
    if len(counts) != 1:
        raise ValueError("All methods must use the same query count before comparison")
    rows = [
        {
            "method": payload["model_name"],
            "artifact": path.name,
            **{metric: float(payload[metric]) for metric in METRICS},
        }
        for path, payload in artifacts
    ]
    best = {metric: max(rows, key=lambda row: row[metric])["method"] for metric in METRICS}
    return {
        "schema_version": "aeroragx.retrieval-comparison.v1",
        "query_count": counts.pop(),
        "methods": rows,
        "best_method_by_metric": best,
        "limitations": [
            "Methods are comparable only because they use the same frozen query set.",
            "Retrieval metrics do not establish answer grounding or domain-expert utility.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.artifacts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
