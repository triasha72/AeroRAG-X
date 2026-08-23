"""Build a deterministic release-readiness report from committed evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from aeroragx.release import (
    build_readiness_report,
    load_readiness_policy,
)


def main() -> int:
    """Run readiness checks and optionally write JSON and Markdown reports."""

    parser = argparse.ArgumentParser(
        description="Check committed AeroRAG-X release evidence.",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("configs/release_readiness_v0_1.yaml"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--allow-unready",
        action="store_true",
        help="Write the truthful report without failing the command when gates remain open.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    policy = load_readiness_policy(args.policy)
    report = build_readiness_report(
        project_root=project_root,
        policy=policy,
    )

    if args.json_output is not None:
        args.json_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.json_output.write_text(
            json.dumps(report.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )

    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.markdown_output.write_text(
            report.to_markdown(),
            encoding="utf-8",
        )

    print(report.to_markdown())

    return 0 if report.passed or args.allow_unready else 1


if __name__ == "__main__":
    raise SystemExit(main())
