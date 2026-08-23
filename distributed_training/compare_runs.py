"""Compare completed baseline and FSDP summaries without inventing parity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("fsdp", type=Path)
    parser.add_argument("--max-val-loss-delta", type=float, default=0.02)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    fsdp = json.loads(args.fsdp.read_text(encoding="utf-8"))
    delta = abs(float(fsdp["validation_loss"]) - float(baseline["validation_loss"]))
    result = {
        "baseline": baseline,
        "fsdp": fsdp,
        "validation_loss_absolute_delta": delta,
        "parity_tolerance": args.max_val_loss_delta,
        "final_model_parity": delta <= args.max_val_loss_delta,
        "resume_validated": bool(fsdp["resume_validated"]),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
