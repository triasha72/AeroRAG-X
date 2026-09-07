# Public human-evidence protocol

This evaluation combines two public datasets with different retrieval shapes.
QASPER checks whether the retriever preserves evidence inside a full paper.
SciFact checks whether it can find an evidence-bearing abstract in a larger
scientific corpus. Both datasets contain human evidence annotations.

SciFact claims and annotations are CC BY 4.0; its S2ORC abstract corpus is
ODC-By 1.0. Source text stays outside Git. The result artifact contains dataset
checksums and aggregate metrics only.

```bash
PYTHONPATH=src python scripts/evaluate_scifact_retrieval.py \
  --corpus data/external/scifact/corpus.jsonl \
  --claims data/external/scifact/claims_dev.jsonl \
  --output artifacts/evaluation/scifact_external_retrieval_v1.json

python scripts/build_author_error_audit.py \
  --output outputs/aerospace_author_audit.jsonl
```

The author audit covers 50 frozen aerospace cases and must disclose
`reviewer_role: project_author`. The combined assessment therefore supports an
offline public-benchmark claim, not an independent aerospace-review claim.

```bash
PYTHONPATH=src python scripts/assess_public_evidence.py \
  --qasper artifacts/evaluation/qasper_external_retrieval_v1.json \
  --scifact artifacts/evaluation/scifact_external_retrieval_v1.json \
  --author-audit outputs/aerospace_author_audit_summary.json \
  --output artifacts/evaluation/public_evidence_assessment_v1.json
```
