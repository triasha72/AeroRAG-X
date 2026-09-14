# External v1

The evaluator creates `private/questions.jsonl` and keeps the ground truth, source notes, and scores in `private/` until the baseline has been scored.

Each question row needs only this for the system run:

```json
{"question_id":"EXT-001","question":"Question text"}
```

Run the frozen system once:

```bash
PYTHONPATH=src python scripts/run_external_evaluation_v0_1.py \
  --questions data/evaluation/external_v1/private/questions.jsonl \
  --output-dir artifacts/evaluation/external_v1/private/baseline \
  --system-version external-eval-v1.0 \
  --git-commit "$(git rev-parse HEAD)"
```

The run writes the answer, claim and citation records, first-pass retrieved passages, and hashes for the frozen inputs. Do not rerun failed questions with changed settings.

After scoring, the evaluator can release the question set, source evidence, scores, and failure labels.
