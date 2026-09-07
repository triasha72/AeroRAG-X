#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:-data/external/trec-rag-2024}"
mkdir -p "$output_dir"

curl -fsSL https://trec.nist.gov/data/rag/topics.rag24.test.txt \
  -o "$output_dir/topics.rag24.test.txt"
curl -fsSL https://trec.nist.gov/data/rag/2024-retrieval-qrels.txt \
  -o "$output_dir/2024-retrieval-qrels.txt"
curl -fsSL \
  https://trec.nist.gov/data/rag/final.citation_judgments_without_prediction.20241025.jsonl \
  -o "$output_dir/final.citation_judgments_without_prediction.20241025.jsonl"

wc -l "$output_dir"/*
