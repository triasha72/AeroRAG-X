#!/usr/bin/env python3
"""Build the frozen claim-evidence support review queue."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CAPTURES = {
    "base_rag": (ROOT / "artifacts" / "evaluation" / "claim_support_base_capture_v0_1.json"),
    "lora_rag": (ROOT / "artifacts" / "evaluation" / "claim_support_lora_capture_v0_1.json"),
}

QUEUE_PATH = ROOT / "artifacts" / "evaluation" / "claim_support_review_queue_v0_1.jsonl"

UNITS_PATH = ROOT / "artifacts" / "evaluation" / "claim_support_review_units_v0_1.jsonl"

PENDING_PATH = ROOT / "artifacts" / "evaluation" / "claim_support_review_pending_v0_1.md"

BATCH_DIR = ROOT / "artifacts" / "evaluation" / "claim_support_review_batches_v0_1"

EXPECTED_COUNTS = {
    "base_rag": 32,
    "lora_rag": 53,
}

BATCH_SIZE = 15

_ALLOWED_MANUAL_LABELS = {
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "UNSUPPORTED",
    "CONTRADICTED",
}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    """Normalize text for conservative exact-containment matching."""

    return " ".join(
        _NON_ALNUM.sub(
            " ",
            text.casefold(),
        ).split()
    )


def load_capture(
    path: Path,
) -> dict[str, object]:
    """Load one frozen claim-support capture."""

    return json.loads(path.read_text(encoding="utf-8"))


def deterministic_exact_support(
    claim_text: str,
    evidence_texts: list[str],
) -> bool:
    """Return true only when the complete claim occurs in cited evidence."""

    normalized_claim = normalize(claim_text)

    if not normalized_claim:
        return False

    return any(normalized_claim in normalize(evidence_text) for evidence_text in evidence_texts)


def review_fingerprint(
    *,
    claim_text: str,
    citations: list[dict[str, object]],
) -> str:
    """Fingerprint identical claim-plus-evidence review tasks."""

    payload = {
        "claim_text": claim_text.strip(),
        "citations": [
            {
                "chunk_id": citation["chunk_id"],
                "evidence_text": citation["evidence_text"],
            }
            for citation in citations
        ],
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> None:
    queue_rows: list[dict[str, object]] = []

    for system, path in CAPTURES.items():
        capture = load_capture(path)

        summary = capture["summary"]

        if not isinstance(
            summary,
            dict,
        ):
            raise TypeError("Capture summary must be a mapping.")

        if not summary["reference_alignment_pass"]:
            raise RuntimeError(f"{system} did not pass reference alignment.")

        query_results = capture["query_results"]

        if not isinstance(
            query_results,
            list,
        ):
            raise TypeError("query_results must be a list.")

        for query_row in query_results:
            query_id = str(query_row["query_id"])

            citations = query_row["citations"]

            claims = query_row["claims"]

            if not isinstance(
                citations,
                list,
            ):
                raise TypeError("citations must be a list.")

            if not isinstance(
                claims,
                list,
            ):
                raise TypeError("claims must be a list.")

            citations_by_id = {str(citation["citation_id"]): citation for citation in citations}

            if len(citations_by_id) != len(citations):
                raise RuntimeError(f"{system}:{query_id} contains duplicate citation IDs.")

            for claim in claims:
                claim_id = str(claim["claim_id"])

                claim_text = str(claim["text"])

                citation_ids = [str(value) for value in claim["citation_ids"]]

                if not citation_ids:
                    raise RuntimeError(f"{system}:{query_id}:{claim_id} has no citations.")

                missing = set(citation_ids) - set(citations_by_id)

                if missing:
                    raise RuntimeError(
                        f"{system}:"
                        f"{query_id}:"
                        f"{claim_id} "
                        "references missing "
                        f"citations: "
                        f"{sorted(missing)}"
                    )

                cited = [citations_by_id[citation_id] for citation_id in citation_ids]

                evidence_texts = [str(citation["evidence_text"]) for citation in cited]

                auto_supported = deterministic_exact_support(
                    claim_text,
                    evidence_texts,
                )

                review_id = f"{system}:{query_id}:{claim_id}"

                queue_rows.append(
                    {
                        "review_id": (review_id),
                        "system": system,
                        "query_id": (query_id),
                        "query": (query_row["query"]),
                        "answer": (query_row["answer"]),
                        "claim_id": (claim_id),
                        "claim_text": (claim_text),
                        "citation_ids": (citation_ids),
                        "citations": (cited),
                        "review_status": (
                            "AUTO_SUPPORTED_EXACT" if auto_supported else "REVIEW_REQUIRED"
                        ),
                        "automatic_label": ("SUPPORTED" if auto_supported else None),
                        "automatic_method": (
                            "normalized_exact_claim_containment" if auto_supported else None
                        ),
                        "human_label": None,
                        "adjudication_note": (None),
                    }
                )

    if len(queue_rows) != 85:
        raise RuntimeError(f"Expected 85 total claims; found {len(queue_rows)}.")

    system_counts = Counter(str(row["system"]) for row in queue_rows)

    if dict(system_counts) != (EXPECTED_COUNTS):
        raise RuntimeError(f"Unexpected system claim counts: {system_counts}")

    review_ids = [str(row["review_id"]) for row in queue_rows]

    if len(review_ids) != len(set(review_ids)):
        raise RuntimeError("Duplicate review IDs.")

    QUEUE_PATH.write_text(
        "".join(
            json.dumps(
                row,
                sort_keys=True,
            )
            + "\n"
            for row in queue_rows
        ),
        encoding="utf-8",
    )

    pending = [row for row in queue_rows if row["review_status"] == "REVIEW_REQUIRED"]

    grouped: dict[
        str,
        list[dict[str, object]],
    ] = defaultdict(list)

    for row in pending:
        citations = row["citations"]

        if not isinstance(
            citations,
            list,
        ):
            raise TypeError("citations must be a list.")

        fingerprint = review_fingerprint(
            claim_text=str(row["claim_text"]),
            citations=citations,
        )

        grouped[fingerprint].append(row)

    units = []

    for index, (
        fingerprint,
        members,
    ) in enumerate(
        sorted(grouped.items()),
        start=1,
    ):
        first = members[0]

        units.append(
            {
                "unit_id": (f"claimrev_{index:03d}"),
                "fingerprint": (fingerprint),
                "claim_text": (first["claim_text"]),
                "query": (first["query"]),
                "citations": (first["citations"]),
                "member_count": (len(members)),
                "member_review_ids": [member["review_id"] for member in members],
                "member_systems": sorted({str(member["system"]) for member in members}),
                "human_label": None,
                "adjudication_note": (None),
            }
        )

    UNITS_PATH.write_text(
        "".join(
            json.dumps(
                unit,
                sort_keys=True,
            )
            + "\n"
            for unit in units
        ),
        encoding="utf-8",
    )

    lines = [
        "# Claim-support review",
        "",
        ("Allowed labels: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`."),
        "",
    ]

    for unit in units:
        lines.extend(
            [
                "---",
                "",
                (f"## {unit['unit_id']}"),
                "",
                ("**Systems:** " + ", ".join(unit["member_systems"])),
                "",
                ("**Claim:** " + str(unit["claim_text"])),
                "",
                "**Cited evidence:**",
                "",
            ]
        )

        citations = unit["citations"]

        if not isinstance(
            citations,
            list,
        ):
            raise TypeError("citations must be a list.")

        for citation in citations:
            lines.extend(
                [
                    (f"- `{citation['citation_id']}` | `{citation['chunk_id']}`"),
                    "",
                    str(citation["evidence_text"]),
                    "",
                ]
            )

        lines.extend(
            [
                ("**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`"),
                "",
                "**Note:**",
                "",
            ]
        )

    PENDING_PATH.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    BATCH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for old_path in BATCH_DIR.glob("batch_*.md"):
        old_path.unlink()

    for batch_start in range(
        0,
        len(units),
        BATCH_SIZE,
    ):
        batch_number = batch_start // BATCH_SIZE + 1

        batch_units = units[batch_start : batch_start + BATCH_SIZE]

        batch_lines = [
            (f"# Claim-support review batch {batch_number:02d}"),
            "",
            ("Allowed labels: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`."),
            "",
        ]

        for unit in batch_units:
            batch_lines.extend(
                [
                    "---",
                    "",
                    (f"## {unit['unit_id']}"),
                    "",
                    ("**Systems:** " + ", ".join(unit["member_systems"])),
                    "",
                    ("**Claim:** " + str(unit["claim_text"])),
                    "",
                    "**Cited evidence:**",
                    "",
                ]
            )

            citations = unit["citations"]

            if not isinstance(
                citations,
                list,
            ):
                raise TypeError("citations must be a list.")

            for citation in citations:
                batch_lines.extend(
                    [
                        (f"- `{citation['citation_id']}` | `{citation['chunk_id']}`"),
                        "",
                        str(citation["evidence_text"]),
                        "",
                    ]
                )

            batch_lines.extend(
                [
                    (
                        "**Decision:** "
                        "`SUPPORTED / "
                        "PARTIALLY_SUPPORTED / "
                        "UNSUPPORTED / "
                        "CONTRADICTED`"
                    ),
                    "",
                    "**Note:**",
                    "",
                ]
            )

        output = BATCH_DIR / (f"batch_{batch_number:02d}.md")

        output.write_text(
            "\n".join(batch_lines) + "\n",
            encoding="utf-8",
        )

    status_counts = Counter(str(row["review_status"]) for row in queue_rows)

    print(
        "total claims:",
        len(queue_rows),
    )
    print(
        "base claims:",
        system_counts["base_rag"],
    )
    print(
        "LoRA claims:",
        system_counts["lora_rag"],
    )
    print(
        "auto-supported exact:",
        status_counts["AUTO_SUPPORTED_EXACT"],
    )
    print(
        "manual instances:",
        len(pending),
    )
    print(
        "unique manual units:",
        len(units),
    )
    print(
        "exact duplicates removed:",
        len(pending) - len(units),
    )
    print(
        "review batches:",
        ((len(units) + BATCH_SIZE - 1) // BATCH_SIZE),
    )
    print(
        "allowed labels:",
        sorted(_ALLOWED_MANUAL_LABELS),
    )
    print("PASS")


if __name__ == "__main__":
    main()
