# Compact generation v0.3.1 development diagnostic

The first eight-case development run tested the explicit-schema compact prompt
with both the Base checkpoint and the reproduced epoch-2 LoRA adapter. It was a
real MPS run over the development-only query file; it did not touch the
protected 32-query set.

| Metric | Base + compact | LoRA + compact |
|---|---:|---:|
| Completed queries | 5 / 8 | 8 / 8 |
| Generation failures | 3 | 0 |
| Answerability accuracy | 0.5000 | 1.0000 |
| Answerable completion | 0.5000 | 1.0000 |
| Unsupported refusal | 0.5000 | 1.0000 |
| Expected-term recall | 0.5000 | 0.9444 |
| Structural validity | 0.6250 | 1.0000 |

This establishes a useful development result: the LoRA treatment followed the
v0.3.1 structure on all eight cases, including both unsupported questions. It
does not establish prompt efficiency. The generated paired report compared Base
compact with LoRA compact, changing both the model condition and output. Its
four paired calls and apparent 13.08% difference are therefore retained only as
a model-condition diagnostic; they are not a compact-prompt claim.

The runner has been corrected to hold the reproduced LoRA checkpoint, retrieval
pipeline, and eight queries fixed. Its control uses the original v0.1 prompt and
512-token ceiling; its treatment uses v0.3.1 and the 384-token ceiling. The next
run will therefore measure the complete compact response policy rather than
confounding it with Base-versus-LoRA behavior.

The three Base failures occurred after provider output but before grounded
citation resolution. The original artifact could not preserve the detailed
reason or token usage at that boundary. The follow-up now attaches a bounded
semantic reason code and provider telemetry to these failures without retaining
raw generated text. This instrumentation change applies only to future runs.

## Corrected same-LoRA comparison

The corrected run held the reproduced epoch-2 LoRA adapter and all retrieval
inputs fixed. Both original v0.1 and compact v0.3.1 completed 8/8 cases with no
failures and perfect answerability, refusal, citation, and structural scores.
Compact expected-term recall was 0.9444 versus 0.8889 for the control.

Across the seven provider-called pairs, compact v0.3.1 reduced mean input tokens
from 2,133.14 to 2,048.43 (-3.97%), output tokens from 166.14 to 163.43
(-1.63%), and total tokens from 2,299.29 to 2,211.86 (-3.80%). The output-token
bootstrap interval was [-41.43, +35.57], and the effect size was -0.046. The
candidate therefore failed only the predeclared 15% output-reduction gate and
was rejected before protected evaluation.

The treatment averaged 2.00 claims against 1.43 in the control, explaining why
shorter instructions did not materially reduce generated output. The next
development candidate, v0.3.2, bounds answers to 80 words, prefers one claim,
allows at most two claims, and lowers the generation ceiling to 256 tokens. It
reuses the frozen control by checksum and remains barred from protected data.

Corrected comparison identity:

- Original-prompt LoRA report: `a63c594d2d97278cbcb64b6e1cf1e52b3d224de8265fb6fe30cb4214b3d01e39`
- Original-prompt telemetry: `39bbd9f06ed87881405ab40d0e6225822735f15e015c421468b8b038c1b2298b`
- Compact-prompt LoRA report: `fd8eb5b63b047dcb445dd62b2629a5f64da647d38b2ad3214ea66def4285e0e2`
- Compact-prompt telemetry: `a59ca19b0ea3203fcd8b89320d07a0dcb57258638d8f11c32007fd378e71c808`
- Paired analysis: `e2ab6138d5200bb80ffb2064a42c49f241166f2ac9add7cbeb3c4ff42392a4b0`
- Fail-closed decision: `1be74176b24185d5ffd7c4a27c9456b38d969de93c288abc249f98f7f1c5cfc3`

## Artifact identity

- Base report: `553b513e6128c6e37d4f62504fcfd6585679bc2f68c7923ef95b8531c138f894`
- Base telemetry: `2c7b068b4087ea906ced4c2f22bf139437a9997e39057b2679d7992eed52e32d`
- LoRA report: `fd8eb5b63b047dcb445dd62b2629a5f64da647d38b2ad3214ea66def4285e0e2`
- LoRA telemetry: `ca978fb182fe982e922bd18a726f69634767ba9d10b80d112ce4812f10b61ca5`
- Base-versus-LoRA diagnostic: `085cae8047d6fefb9793bbb0168daa889ff3fbd560907be295f9fb43cf15de6a`
