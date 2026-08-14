# Multimodal page rendering v0.1

## Purpose

This phase adds a small, cross-platform foundation for rendering selected NASA
technical-report pages as PNG files.

It renders only whole PDF pages that are already referenced by validated
`VisualAssetRecord` values. It does not identify figures or tables from pixels,
crop images, run OCR, create embeddings, change retrieval, or expose an API.

## Input gate

`render_visual_asset_pages()` accepts only `VisualAssetRecord` instances. It
revalidates every record before work begins, rejects duplicate asset IDs, and
deduplicates valid assets by source page.

One PDF page can contain multiple visual assets. Therefore the output contains
one `PageRenderRecord` and one PNG per unique referenced page, not one PNG per
asset. For example, the manually verified evaluation slice references two
assets on page 60 and two assets on page 84, so each page is rendered once.

Before PDFium opens a source document or an output directory is created, the
renderer checks that the local source file exists and that its SHA-256 checksum
matches the checksum preserved by the visual-asset provenance record.

## Renderer

The implementation uses:

- `pypdfium2` to load a PDF, select its zero-based page index, and render a
  bitmap at `dpi / 72` scale.
- `Pillow` to save the bitmap as a PNG with the requested DPI metadata.

The default is 144 DPI. Rendering is intentionally sequential because PDFium
does not support simultaneous calls from multiple threads.

## Output contract

Each `PageRenderRecord` contains:

- deterministic PDF page identity: document ID, page ID, and page number
- source path, source URL, NASA citation URL, and source-PDF SHA-256 checksum
- deterministic PNG path: `{output_directory}/{document_id}/page_{page:04d}.png`
- PNG SHA-256 checksum
- rendered width and height in pixels
- requested DPI
- renderer name and installed renderer version

Rendered PNG files belong under `data/derived/multimodal/page_renders/`. That
directory is intentionally ignored by Git: PNG outputs are local derived
artifacts, while the code and provenance records remain version controlled.

## Scope boundary

This foundation does not add:

- corpus reprocessing
- OCR or text extraction changes
- figure/table detection, segmentation, or cropping
- visual embeddings or multimodal retrieval
- generation, evaluation, CLI, API, or model changes

The next multimodal phase can use page renders only after a separately defined,
versioned, and evaluated asset-extraction approach is approved.
