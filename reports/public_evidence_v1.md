# Public evidence and citation failure checks

This evaluation uses evidence that can be reproduced without paid reviewers.
It does not rename automated checks as human judgment.

## What ran

| Check | Result | What it tells us |
|---|---:|---|
| QASPER evidence retrieval | Recall@20 `0.6768` | Retrieval on human-authored scientific questions |
| SciFact evidence documents | Recall@10 `0.8989` | Retrieval of expert-annotated scientific evidence |
| TREC 2024 RAG retrieval labels | `20,283` | Public independent relevance judgments are available |
| TREC 2024 citation labels | `2,840` | Public independent citation-support judgments are available |
| NASA wrong-source corruption | `200/200` detected | Exact source-ID provenance failures are rejected |
| NASA author audit | Pending | Natural aerospace answer and citation errors still need review |

The TREC artifact is a source and label audit, not an AeroRAG-X score. Running
the retriever on TREC requires the matching MS MARCO v2.1 passage collection,
which is not copied into this repository.

The corruption suite is intentionally narrow. It proves that a cited chunk must
belong to the frozen relevant set. It cannot decide whether a fluent sentence
adds a claim that the cited paragraph only partly supports.

## Remaining gap

Complete `data/evaluation/source_grounded_author_audit_v1.template.jsonl` and
run `scripts/summarize_author_error_audit.py`. That produces the disclosed
50-case error breakdown required by the public-evidence gate. Independent
aerospace expert review remains useful future work, not a hidden release
dependency.
