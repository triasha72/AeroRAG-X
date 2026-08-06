# AeroRAG-X Retrieval Evaluation Dataset

## Version

Evaluation dataset version: `v0.1`

## Purpose

This dataset provides an initial benchmark for evaluating retrieval
systems over the AeroRAG-X NASA technical-report corpus.

## Corpus

- Source: NASA Technical Reports Server documents
- Retrieval unit: citation-preserving text chunk
- Corpus size at benchmark creation: 3,233 chunks
- Chunking configuration: `configs/chunking_v0_1.yaml`

## Files

- `queries_v0_1.jsonl`: natural-language aerospace retrieval queries
- `candidates_v0_1.jsonl`: top BM25 candidates reviewed during annotation
- `qrels_v0_1.jsonl`: human-selected relevant chunk IDs

## Evaluation Metrics

- Recall@5
- Recall@10
- MRR@10
- NDCG@10

## Annotation Protocol

For each query, the top BM25 candidates were reviewed manually.
Chunks were marked relevant when they directly addressed the technical
topic, contained useful evidence, and preserved valid document and page
provenance.

## Known Limitation

The relevance judgments were created from a BM25-generated candidate
pool. This may favor BM25 because relevant results retrieved only by
future dense or hybrid systems were not included in the original pool.

A future `v0.2` dataset should pool and deduplicate results from BM25,
dense retrieval, and hybrid retrieval before relevance annotation.

## Reproducibility

The benchmark report is stored at:

`artifacts/evaluation/bm25_v0_1.json`
