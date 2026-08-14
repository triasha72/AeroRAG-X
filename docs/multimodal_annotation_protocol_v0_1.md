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

There may be at most one response per `(task_id, annotator_id)` pair.

Real v0.1 review responses are expected at:

```text
artifacts/evaluation/multimodal_annotation_responses_v0_1/reviewer_a.jsonl
artifacts/evaluation/multimodal_annotation_responses_v0_1/reviewer_b.jsonl
```

Do not fabricate response files to make the finalizer pass.

## Raw agreement helper

`summarize_multimodal_annotation_agreement` accepts known tasks, responses, and
two distinct annotator IDs. It rejects unknown task IDs and duplicate reviewer
responses, then reports:

```text
comparable_task_count
exact_match_count
exact_match_rate
disagreement_task_ids
```

This helper intentionally summarizes only tasks shared by the two selected
reviewers. It is useful for intermediate analysis, but it does not establish
that the entire frozen review set has been independently completed.

For example:

```text
Frozen tasks: 5
Reviewer A completed: 5
Reviewer B completed: 1
Shared tasks: 1
Shared-task exact agreement: 1 / 1
```

That is not a complete independent review.

## Complete-review evidence gate

Final Phase 35 review evidence must use:

```text
validate_complete_multimodal_annotation_review
```

The complete-review validator requires:

```text
two distinct reviewer IDs
        ↓
every response references a known frozen task
        ↓
no unselected reviewer IDs
        ↓
Reviewer A covers every frozen task exactly once
        ↓
Reviewer B covers every frozen task exactly once
        ↓
raw exact agreement may be finalized
```

For the current five-task slice, successful finalization therefore requires:

```text
5 reviewer_a responses
+
5 reviewer_b responses
=
10 validated responses
```

Partial overlap cannot produce final evidence.

Successful validation produces a `MultimodalAnnotationEvidenceSummary` with:

```text
task_version
evaluation_name
task_count
annotator_ids
response_count
complete_review
comparable_task_count
exact_match_count
exact_match_rate
decision_counts_by_annotator
disagreement_task_ids
adjudication_required
```

The summary is raw exact-decision agreement only. It is not a chance-corrected
inter-annotator reliability statistic.

## Independent-review and adjudication policy

1. Reviewer A and Reviewer B complete their initial passes independently.
2. Neither reviewer inspects the other reviewer's decisions before both passes
   are complete.
3. Original reviewer response files remain unchanged after submission.
4. Any unequal decisions constitute a disagreement.
5. `uncertain` is a valid decision and is not forced into a binary label.
6. Disagreements are examined only after both independent passes are frozen.
7. Any adjudicated result is stored in a separate versioned artifact.
8. The adjudication record preserves both original decisions and a written
   rationale.
9. Raw independent agreement and adjudicated consensus are reported separately.

If real disagreements exist, a later adjudication artifact may include:

```text
task_id
reviewer_a_decision
reviewer_b_decision
final_decision
adjudication_rationale
```

The exact adjudication schema should be implemented only when there are real
disagreements to record.

## Finalization

After both genuine independent review files exist:

```bash
python scripts/finalize_multimodal_annotation_v0_1.py
```

The finalizer refuses to produce evidence when either reviewer has incomplete
coverage.

Expected outputs after successful finalization are:

```text
artifacts/evaluation/multimodal_annotation_agreement_v0_1.json
reports/multimodal_annotation_agreement_v0_1.md
```

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
python -m mypy scripts/finalize_multimodal_annotation_v0_1.py
python -m pytest -q \
  tests/test_multimodal_annotation.py \
  tests/test_multimodal_annotation_finalization.py
git diff --check
```

## Interpretation limits

The current v0.1 slice contains only five positive visual-asset records from
one source document.

Therefore:

```text
raw reviewer agreement
!=
general multimodal retrieval quality
```

and:

```text
verified positive assets
!=
figure/table detection benchmark
```

No OCR, detection, extraction, visual embedding, multimodal retrieval, or
multimodal generation quality claim should be made from the v0.1 review slice
alone.

## Next evidence needed

Before broader multimodal claims, the project needs genuine independent review
of the frozen v0.1 tasks, then a larger separately versioned multimodal
candidate set with independent annotation. Automatic figure/table detection,
caption association, structured table extraction, visual retrieval, and OCR
remain downstream capabilities.
