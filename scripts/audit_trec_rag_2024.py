#!/usr/bin/env python3
"""Audit downloaded official TREC 2024 RAG human judgments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.evaluation.trec_rag import summarize_trec_rag


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", type=Path, required=True)
    parser.add_argument("--retrieval-qrels", type=Path, required=True)
    parser.add_argument("--citation-judgments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize_trec_rag(args.topics, args.retrieval_qrels, args.citation_judgments)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
