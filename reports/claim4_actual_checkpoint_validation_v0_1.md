# Actual checkpoint claim-four validation v0.1

## Why this run exists

The original comparison showed that LoRA's extra token cost came from generated
output, not retrieved input. Reducing evidence would have weakened grounding,
and sharply reducing the generation limit risked truncated JSON. The controlled
decision was therefore to reduce the maximum claim count from six to four while
holding retrieval and validation fixed.

The missing epoch-2 adapter was reconstructed with the complete three-epoch
Apple MPS treatment. It reproduced the selected development loss exactly after
reload. The frozen NTRS corpus and dense index were rebuilt from checksummed
receipts.

## Execution decision

A monolithic validation was killed with exit 137 because the dense encoder,
reranker, and Qwen shared 16 GB of unified memory. The completed run used the
same 32 queries and settings but separated retrieval from generation: it
computed exact reranked top-five hit sets, released retrieval models, and then
loaded Qwen. No query, checkpoint, token limit, or evidence was compressed or
substituted.

## Measured results

| Metric | Base + RAG | LoRA + RAG |
|---|---:|---:|
| Query attempts | 32 | 32 |
| Completed | 31 | 30 |
| Failures | 1 | 2 |
| Answerability accuracy | 0.90625 | 0.87500 |
| Answerable completion | 0.95000 | 0.90000 |
| Unsupported refusal | 0.83333 | 0.83333 |
| Citation coverage | 1.00000 | 1.00000 |
| Citation validity | 1.00000 | 1.00000 |
| Source-document coverage | 1.00000 | 1.00000 |
| Expected-term recall | 0.89655 | 0.84483 |
| Structural validity | 0.96875 | 0.93750 |
| Total claims | 26 | 44 |
| Provider input tokens | 47,339 | 45,443 |
| Provider output tokens | 2,992 | 4,245 |
| Provider total tokens | 50,331 | 49,688 |
| Provider calls | 21 | 20 |
| Mean output tokens/call | 142.48 | 212.25 |
| P50 provider latency | 8.76 s | 13.68 s |
| P95 provider latency | 64.96 s | 20.30 s |

Base failed `synth_003` at the provider transport boundary. LoRA failed
`core_005` at the provider transport boundary and `para_005` during generation
validation. The conditions therefore have different successful-call counts.

## Interpretation

LoRA's aggregate total was 643 tokens lower, but that is confounded by one
fewer provider call and one additional failure. It is not a token-efficiency
win. Per call, LoRA generated about 49.0% more output tokens and 69.2% more
claims. Four claims reduced LoRA output relative to the historical six-claim
run, but did not remove the Base/LoRA verbosity gap.

The next defensible optimization is paired analysis over queries completed by
both conditions, followed by a leaner response schema that retains evidence IDs
and citation validation. Evidence top-k stays fixed until an ablation shows
grounding quality is preserved.

That paired analysis is now complete. On the 19 token-observed calls shared by
both conditions, LoRA averaged 210.89 output tokens and Base averaged 140.89
(+49.68%). LoRA was longer on 16 paired calls. The result and per-query rows are
in `artifacts/evaluation/generation_claim4_paired_efficiency_v0_1.json` and
`reports/generation_claim4_paired_efficiency_v0_1.md`.

## Artifact identity

- Base report SHA-256: `1fba3dd3d731a9cb6559b0ddb0cf8e26e92f46eb2eced9bedb49385b591f423c`
- LoRA report SHA-256: `7f6379a10aa7eaf61821d38f4c78b5298cea9228ffff655636b6945841af8603`
- Base telemetry SHA-256: `6d59fddb625d144fbc9219169642f3fa71e561a3eb7db82e394025394b69f100`
- LoRA telemetry SHA-256: `7801f929c4af524b9ac3b87d8a094b394fecd6505cedb9aaeca51e2d4e45a6f8`
- Completion manifest SHA-256: `f73edff666a47d673263c40ab76463357171f166496ef49ddd163632f99c4e67`
- Adapter SHA-256: `13df5eb8449d5b204c2d740b0c194b7712969f15258c42b26a336febeb27c717`
