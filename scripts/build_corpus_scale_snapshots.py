"""Build reproducible logical 10K, 100K, and 1M corpus snapshot manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.retrieval.bm25 import load_chunk_records
from aeroragx.retrieval.scaling import build_scale_snapshot_manifest


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--targets", type=int, nargs="+", default=[10_000, 100_000, 1_000_000])
    parser.add_argument("--seed", type=int, default=1729)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    chunks = load_chunk_records(args.chunks)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    for target in args.targets:
        manifest = build_scale_snapshot_manifest(
            source_path=args.chunks,
            authoritative_chunk_count=len(chunks),
            target_chunk_count=target,
            seed=args.seed,
        )
        output = args.output_directory / f"corpus_scale_{target}_v0_1.json"
        output.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(output)


if __name__ == "__main__":
    main()
