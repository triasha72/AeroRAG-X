# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **22**. Paired provider calls: **12**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean output tokens | 207.75 | 158.25 |
| Mean claims | 2.08 | 1.42 |
| Mean repeated-word fraction | 0.2458 | 0.1785 |

Mean treatment-minus-Base output delta: **-49.50 tokens**.
Paired bootstrap 95% interval: **[-80.42, -23.25] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **-0.944**.
Relative treatment output change: **-23.83%**.
Treatment used fewer/equal/more tokens on **10 / 0 / 2** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
