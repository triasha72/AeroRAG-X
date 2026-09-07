#!/usr/bin/env python3
"""Combine public human-evidence results with a disclosed author audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.evaluation.public_evidence import assess_public_evidence


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qasper", type=Path, required=True)
    parser.add_argument("--scifact", type=Path, required=True)
    parser.add_argument("--author-audit", type=Path)
    parser.add_argument("--trec-rag", type=Path)
    parser.add_argument("--citation-corruption", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess_public_evidence(
        load(args.qasper),
        load(args.scifact),
        None if args.author_audit is None else load(args.author_audit),
        None if args.trec_rag is None else load(args.trec_rag),
        None if args.citation_corruption is None else load(args.citation_corruption),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"decision={result['decision']} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
