"""Build a normalized large-scale snapshot from real corpus text.

The output contains retrieval segments plus parent references. Document metadata stays
in the source corpus, avoiding the cost of repeating it for every smaller segment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-chunks", type=int, required=True)
    parser.add_argument("--segment-words", type=int, default=80)
    parser.add_argument("--overlap-words", type=int, default=16)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if args.segment_words <= args.overlap_words:
        raise ValueError("segment-words must be greater than overlap-words")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    digest = hashlib.sha256()
    step = args.segment_words - args.overlap_words
    with args.source.open(encoding="utf-8") as source, args.output.open("wb") as output:
        for line in source:
            parent = json.loads(line)
            words = str(parent.get("text", "")).split()
            for index, start in enumerate(range(0, len(words), step)):
                window = words[start : start + args.segment_words]
                if not window:
                    continue
                record = {
                    "chunk_id": f"{parent['chunk_id']}:segment:{index:03d}",
                    "parent_chunk_id": parent["chunk_id"],
                    "document_id": parent["document_id"],
                    "page_start": parent.get("page_start"),
                    "page_end": parent.get("page_end"),
                    "text": " ".join(window),
                }
                encoded = (json.dumps(record, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
                output.write(encoded)
                digest.update(encoded)
                count += 1
                if count >= args.target_chunks:
                    break
                if start + args.segment_words >= len(words):
                    break
            if count >= args.target_chunks:
                break
    manifest = {
        "version": "0.1",
        "snapshot_kind": "real-content-load-scale",
        "source_chunks": str(args.source),
        "chunk_count": count,
        "target_chunk_count": args.target_chunks,
        "complete": count == args.target_chunks,
        "segment_words": args.segment_words,
        "overlap_words": args.overlap_words,
        "chunks_sha256": digest.hexdigest(),
        "limitation": "Segments reuse real source chunks; this tests retrieval load, not corpus breadth.",
    }
    manifest_path = args.output.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
