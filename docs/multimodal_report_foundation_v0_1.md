# Multimodal report foundation v0.1

## Purpose

This correction documents the strict, page-linked provenance contract for future visual assets in NASA technical reports.

A visual asset is currently limited to a future `figure` or `table`. This work does not claim that any asset has been detected, extracted, interpreted, or retrieved.

## Contract

Each `VisualAssetRecord` preserves:

- deterministic asset ID
- document ID, page ID, and page number
- figure or table type and page-local index
- optional caption text
- source path and source URL
- NASA citation URL
- source-document SHA-256 checksum

The deterministic identifier is:

```text
{document_id}:page:{page_number}:{asset_type}:{asset_index:03d}