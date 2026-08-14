# Multimodal page-render manifest v0.1

## Purpose

This phase adds a reproducible, local manifest for the pages rendered from the
manually verified multimodal evaluation slice. It connects the existing
page-rendering foundation to a deterministic JSONL artifact without widening the
application runtime.

The runner reads only validated `VisualAssetRecord` values, renders each unique
referenced PDF page, and writes one `PageRenderRecord` per output PNG. A page
with both a figure and a table still produces one PNG and one manifest row.

## Input and validation

The default input is:

```text
data/evaluation/multimodal_report_slice_v0_1.jsonl
```

The source PDF path and SHA-256 checksum are preserved in every visual-asset
record. Before rendering each page, the underlying renderer verifies that the
local PDF exists and that its checksum matches. A failed check prevents that
page from rendering, and the runner writes no manifest unless all requested
pages render successfully.

## Reproduce locally

With the source PDF available at its recorded `source_path`, run:

```bash
python scripts/render_multimodal_report_slice_v0_1.py
```

The default command renders the three unique pages referenced by the v0.1 slice:
pages 60, 61, and 84 of NASA NTRS document `20050228985`.

Optional paths and resolution are explicit:

```bash
python scripts/render_multimodal_report_slice_v0_1.py \
  --assets-input data/evaluation/multimodal_report_slice_v0_1.jsonl \
  --output-directory data/derived/multimodal/page_renders \
  --manifest-output \
    data/derived/multimodal/page_renders/multimodal_report_slice_v0_1_page_renders.jsonl \
  --dpi 144
```

## Output contract

The runner writes:

```text
data/derived/multimodal/page_renders/{document_id}/page_{page:04d}.png
data/derived/multimodal/page_renders/multimodal_report_slice_v0_1_page_renders.jsonl
```

Every manifest row includes page identity, source provenance, PDF checksum, PNG
path and checksum, pixel dimensions, DPI, renderer name, and renderer version.
Rows are revalidated, sorted by document and page, and serialized with sorted
JSON keys. Duplicate page IDs and duplicate PNG paths are rejected.

The entire `data/derived/multimodal/page_renders/` directory is ignored by Git.
The manifest and PNGs are reproducible local derived artifacts, not committed
corpus data.

## Scope boundary

This is a standalone local runner, not an AeroRAG-X API or CLI runtime mode. It
does not add OCR, table-cell extraction, figure/table detection, crops, visual
embeddings, visual retrieval, multimodal generation, model changes, or updates
to protected text-only evaluation data.
