# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **8**. Paired provider calls: **7**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean input tokens | 2133.14 | 1380.86 |
| Mean output tokens | 166.14 | 163.43 |
| Mean total tokens | 2299.29 | 1544.29 |
| Mean claims | 1.43 | 1.86 |
| Mean repeated-word fraction | 0.2502 | 0.2172 |

Mean treatment-minus-Base input delta: **-752.29 tokens** (**-35.27%**).
Mean treatment-minus-Base output delta: **-2.71 tokens**.
Paired bootstrap 95% interval: **[-41.86, +30.57] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **-0.051**.
Relative treatment output change: **-1.63%**.
Mean treatment-minus-Base total delta: **-755.00 tokens** (**-32.84%**).
Treatment used fewer/equal/more tokens on **3 / 1 / 3** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
