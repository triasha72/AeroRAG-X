# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **8**. Paired provider calls: **7**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean input tokens | 2133.14 | 2048.43 |
| Mean output tokens | 166.14 | 163.43 |
| Mean total tokens | 2299.29 | 2211.86 |
| Mean claims | 1.43 | 2.00 |
| Mean repeated-word fraction | 0.2502 | 0.1723 |

Mean treatment-minus-Base input delta: **-84.71 tokens** (**-3.97%**).
Mean treatment-minus-Base output delta: **-2.71 tokens**.
Paired bootstrap 95% interval: **[-41.43, +35.57] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **-0.046**.
Relative treatment output change: **-1.63%**.
Mean treatment-minus-Base total delta: **-87.43 tokens** (**-3.80%**).
Treatment used fewer/equal/more tokens on **5 / 0 / 2** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
