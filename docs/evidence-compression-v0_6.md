# Source-preserving evidence compression v0.6

## Engineering hypothesis

The protected fixed-top-3 experiment saved about one-third of total tokens but
lost answerable coverage. The adaptive 3→5 development run then behaved almost
exactly like fixed top-3, and a 478-candidate scan found only one genuine binary
sufficiency recovery opportunity. Passage count is therefore the wrong control
surface for the next experiment.

v0.6 keeps all five reranked sources and shortens text inside each passage. For
every hit, it ranks sentence segments by query-term overlap, retains at most
two in their original source order, and applies a 1,200-character per-passage
ceiling. At least one non-empty excerpt is retained per hit. Chunk IDs, document
IDs, page ranges, URLs, ranks, and document hashes are unchanged.

Compression occurs before sufficiency assessment and generation. It never uses
model output, never removes an entire selected source, and records original and
compressed character counts plus source chunk IDs for every query.

## Development gate

`scripts/run_evidence_compression_dev_v0_6.sh` compares uncompressed top-5 with
compressed top-5 on the frozen 50-case development set. Advancement requires at
least 15% paired total-token reduction, at least 25 paired calls, no additional
failures, and no quality regression larger than 0.02. Fixed uncompressed top-5
remains the default until a later candidate passes both development and a newly
versioned held-out evaluation.
