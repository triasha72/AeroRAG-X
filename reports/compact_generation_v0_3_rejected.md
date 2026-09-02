# Compact generation v0.3 — completed and rejected

The complete protected 32-query MPS experiment ran for both Base and the
reproduced epoch-2 LoRA adapter. No query was removed and no checkpoint was
substituted. The compact candidate reduced output length on successful matched
LoRA calls, but it failed the reliability and quality gates and was not
promoted.

| Metric | Base compact | LoRA compact |
|---|---:|---:|
| Queries | 32 | 32 |
| Completed | 10 | 22 |
| Generation failures | 22 | 10 |
| Answerability accuracy | 0.3125 | 0.6250 |
| Answerable completion | 0.0000 | 0.5000 |
| Expected-term recall | 0.0000 | 0.4655 |
| Structural validity | 0.3125 | 0.6875 |
| Citation coverage / validity | 1.0000 / 1.0000 | 1.0000 / 1.0000 |

Across 12 successful, token-observed original-LoRA/compact-LoRA pairs, output
fell from 207.75 to 158.25 tokens: -49.50 tokens, or -23.83%. The deterministic
bootstrap 95% interval was [-80.42, -23.25] tokens and Cohen's dz was -0.944.
Compact output was shorter on 10 of 12 calls. This token saving is not a win:
failures increased from 2 in original LoRA to 10 in compact LoRA, and the
promotion gate rejected the candidate.

Base compact and LoRA compact had ten jointly completed queries but zero jointly
successful token-observed provider calls. Their paired report is therefore
`insufficient_paired_observations`; zero-token failures are not converted into
measurements.

The dominant recorded failure stage was response-schema validation. v0.3
telemetry retained only the exception class, so it cannot identify the exact
invalid fields after the fact without storing raw output. The follow-up hardens
future telemetry with bounded field locations and error codes plus token usage,
while continuing to exclude prompts and raw generated text.

## Artifact identity

- Base report SHA-256: `a2fee2e3495dd2ed3aadf8289df573475ca40b31e6129dadd445a6a5f8f6d697`
- Base telemetry SHA-256: `1f736830760fd1b5e425752afdb560509944c724d5cc29db28371dabdf8280a9`
- LoRA report SHA-256: `55d3b430bc7bc91511ee3f3d6ce4abbf6b5b4009fbaa803c2d65990681af2823`
- LoRA telemetry SHA-256: `e76f00d6b39d730f04652bf564c90d3b63b67cfc57650ffe89b6fa6294f6fd3d`
- Original-LoRA comparison SHA-256: `f5de684c6ad0603e818a044a1ba75770b58449c3ce7f03cfbe59514a02b3f60c`
- Promotion decision SHA-256: `0b7dce703dfed82a9dfc1a1a646350c3965e9098547c07520e2931757f523abe`

## Next candidate policy

`grounded-json-v0.3.1-compact-dev` adds an explicit minimal JSON skeleton. It
may be evaluated only on
`data/evaluation/generation_queries_compact_dev_v0_1.jsonl`. The development
runner emits no protected promotion claim. A new protected run is allowed only
after development evidence shows stable schema completion and the candidate is
frozen without consulting protected outcomes.
