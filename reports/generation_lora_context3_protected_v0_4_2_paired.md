# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **31**. Paired provider calls: **16**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean input tokens | 2169.06 | 1381.12 |
| Mean output tokens | 179.19 | 187.50 |
| Mean total tokens | 2348.25 | 1568.62 |
| Mean claims | 1.44 | 1.81 |
| Mean repeated-word fraction | 0.1990 | 0.2140 |

Mean treatment-minus-Base input delta: **-787.94 tokens** (**-36.33%**).
Mean treatment-minus-Base output delta: **+8.31 tokens**.
Paired bootstrap 95% interval: **[-31.75, +45.62] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **+0.104**.
Relative treatment output change: **+4.64%**.
Mean treatment-minus-Base total delta: **-779.62 tokens** (**-33.20%**).
Treatment used fewer/equal/more tokens on **7 / 1 / 8** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
