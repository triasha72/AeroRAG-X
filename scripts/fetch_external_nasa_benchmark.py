#!/usr/bin/env python3
"""Fetch a revision-pinned external NASA benchmark and write a receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", choices=("nasa_sme", "nasa_sde_scale"))
    parser.add_argument(
        "--config", type=Path, default=Path("configs/external_benchmarks_v0_1.yaml")
    )
    parser.add_argument("--output-root", type=Path, default=Path("work/external_benchmarks"))
    parser.add_argument("--receipt-output", type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_spec(path: Path, benchmark: str) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(payload["benchmarks"][benchmark])


def main() -> None:
    args = parse_args()
    spec = load_spec(args.config, args.benchmark)
    destination = args.output_root / args.benchmark / spec["revision"]
    receipts: list[dict[str, object]] = []

    for relative_name in spec["files"]:
        target = destination / relative_name
        target.parent.mkdir(parents=True, exist_ok=True)
        url = (
            f"https://huggingface.co/datasets/{spec['repository']}/resolve/"
            f"{spec['revision']}/{relative_name}?download=true"
        )
        if not target.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "AeroRAG-X/0.1"})
            with urllib.request.urlopen(request) as response, target.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
        receipts.append(
            {
                "path": str(target),
                "bytes": target.stat().st_size,
                "sha256": sha256(target),
                "source_url": url,
            }
        )

    receipt = {
        "receipt_version": "0.1",
        "benchmark": args.benchmark,
        "repository": spec["repository"],
        "revision": spec["revision"],
        "license": spec["license"],
        "evidence_class": spec["evidence_class"],
        "files": receipts,
    }
    receipt_path = destination / "download_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if args.receipt_output is not None:
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
        args.receipt_output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
