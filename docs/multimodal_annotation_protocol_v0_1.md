# Multimodal annotation protocol v0.1

## Purpose

This protocol creates deterministic, page-linked review tasks for the existing
multimodal report slice. Its purpose is to make independent review possible
before AeroRAG-X uses the slice for detection, extraction, retrieval, or model
quality claims.

The protocol does not add automatic figure/table detection, OCR, cropping,
table-cell extraction, visual embeddings, retrieval, API support, or model
changes.

## Frozen inputs

The task builder reads only:

```text
data/evaluation/multimodal_report_slice_v0_1.jsonl
```

That file contains five manually verified `VisualAssetRecord` entries from NASA
NTRS document `20050228985`. Every input record preserves its document ID,
page ID, source path and URLs, NASA citation URL, and source-PDF SHA-256
checksum.

The builder writes this versioned task set:

```text
data/evaluation/multimodal_annotation_tasks_v0_1.jsonl
```

Task rows contain no human decisions. They are assignments for independent
review, not evidence that a second annotator has already reviewed the slice.

## Task contract

Each `MultimodalAnnotationTask` has:

```text
task_id
task_version
task_kind
asset_id
document_id
page_id
page_number
asset_type
asset_index
caption_text
source_path
source_url
citation_url
document_sha256
```

The only v0.1 `task_kind` is:

```text
asset_record_verification
```

Identifiers are deterministic:

```text
page_id = {document_id}:page:{page_number}
asset_id = {page_id}:{asset_type}:{asset_index:03d}
task_id = {asset_id}:annotation:v0_1
```

The task builder revalidates every source `VisualAssetRecord`, rejects duplicate
asset IDs, and writes tasks in document/page/type/index order.

## Independent review instructions

For each task, a reviewer should inspect the cited source page, or a
checksum-verified render regenerated from that source page, and decide whether
the page-linked asset record is accurate.

The reviewer records one of:

| Decision | Meaning |
|---|---|
| `confirmed` | The specified figure/table, page, and supplied caption relationship are supported by the source page. |
| `rejected` | The asset record is inconsistent with the source page. |
| `uncertain` | The reviewer cannot establish the relationship reliably from the source page. |

An absent caption is valid only when the record explicitly contains
`caption_text: null`; reviewers must not invent caption text.

Reviewers should work independently, retain uncertainty rather than force a
decision, and use stable non-sensitive reviewer IDs such as `reviewer_a` and
`reviewer_b`. The task set contains only positive visual-asset records. It is
not yet a figure/table detection benchmark and cannot measure detection recall
or false-positive rate.

## Response contract

Each `MultimodalAnnotationResponse` contains:

```text
task_id
annotator_id
decision
notes
```

There may be at most one response per `(task_id, annotator_id)` pair. Responses
must be stored in a separately versioned JSONL file when real review begins;
this v0.1 pull request intentionally adds no invented response data.

## Agreement summary

`summarize_multimodal_annotation_agreement` accepts known tasks, responses, and
two distinct annotator IDs. It rejects unknown task IDs and duplicate reviewer
responses, then reports:

```text
comparable_task_count
exact_match_count
exact_match_rate
disagreement_task_ids
```

This is a raw exact-decision agreement summary only. It is not a
chance-corrected inter-annotator reliability statistic, and no agreement value
is claimed until two independent response files exist.

## Reproducibility

Build the checked-in task data from its frozen input:

```bash
python scripts/build_multimodal_annotation_tasks_v0_1.py
```

Then verify the change set:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src/aeroragx
python -m mypy scripts/build_multimodal_annotation_tasks_v0_1.py
python -m pytest -q tests/test_multimodal_annotation.py
git diff --check
```

## Next evidence needed

Before the project claims multimodal evaluation results, it needs a larger
versioned candidate set, independently completed response files, a documented
adjudication policy, and an agreement analysis appropriate to the expanded
label distribution.
