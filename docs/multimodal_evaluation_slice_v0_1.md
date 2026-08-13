# Multimodal report evaluation slice v0.1

## Purpose

This is a small, manually verified, page-linked evaluation slice for future figure-aware and table-aware AeroRAG-X work.

It records visual assets without changing the existing text-RAG pipeline.

## Canonical source

All selected assets come from one immutable NASA NTRS source document:

- document ID: `20050228985`
- source PDF: `data/raw/ntrs/v0_1/20050228985.pdf`
- source URL: `https://ntrs.nasa.gov/api/citations/20050228985/downloads/20050228985.pdf`
- citation URL: `https://ntrs.nasa.gov/citations/20050228985`
- SHA-256: `38ffad19c7c2d61858a97ccc8c225d35254b63808140365b213382d2af3c5d6b`

## Manually verified positive assets

| Page | Asset ID | Type | Manual decision |
|---:|---|---|---|
| 60 | `20050228985:page:60:figure:000` | figure | Conductivity bar chart |
| 60 | `20050228985:page:60:figure:001` | figure | Two-panel elastomer photograph with one shared caption |
| 61 | `20050228985:page:61:figure:000` | figure | Composite engine rendering and combustor photograph with one shared caption |
| 84 | `20050228985:page:84:figure:000` | figure | Permeability line chart |
| 84 | `20050228985:page:84:table:000` | table | Material and Darcian-permeability table |

Each asset is represented as a page-linked `VisualAssetRecord` in `data/evaluation/multimodal_report_slice_v0_1.jsonl`.

## Negative control

`20050228985:page:101` was manually inspected and contains no figure or table. It is retained as a documented negative control and deliberately has no `VisualAssetRecord`.

## Deliberate limitations

This slice contains page-level asset references only. It does not include figure crops, bounding boxes, render settings, detection, OCR, table-cell extraction, image embeddings, a visual index, or changes to retrieval, reranking, generation, API behavior, citations, model weights, benchmarks, corpus processing, or protected evaluation data.

## Next decision gate

A later, separately reviewed step may add deterministic page rendering or region-level extraction. That step must retain this exact source-page provenance and be evaluated separately from the frozen text-RAG baseline.
