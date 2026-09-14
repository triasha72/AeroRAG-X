#!/usr/bin/env python3
"""Verify a saved AeroRAG-X API response and emit a safe demo receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.demo_verification import verify_demo_response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.response.read_text(encoding="utf-8"))
    receipt = verify_demo_response(payload)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
