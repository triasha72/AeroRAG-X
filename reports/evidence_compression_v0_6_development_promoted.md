# Evidence compression v0.6 — development gate passed

The real 50-query comparison completed with 47 paired successful provider
calls. Query-aware extractive compression kept all five source hits while
reducing paired total tokens by **57.14%**. The treatment had zero generation
failures versus three in the uncompressed control, answerability accuracy of
0.94 versus 0.88, expected-term recall of 0.562 versus 0.486, and structural
validity of 1.00 versus 0.94.

This is a development result, not a protected-set claim. The apparent quality
improvement is descriptive and can reflect the frozen development sample. The
next step is a newly versioned held-out evaluation with independent review;
fixed uncompressed top-5 remains the operational default until that evidence
exists.

The checksum inventory is recorded in
`artifacts/evaluation/generation_lora_compressed5_dev_v0_6_manifest.json`.
