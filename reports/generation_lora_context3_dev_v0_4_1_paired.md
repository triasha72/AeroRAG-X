# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **46**. Paired provider calls: **40**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean input tokens | 2304.10 | 1523.45 |
| Mean output tokens | 160.20 | 153.70 |
| Mean total tokens | 2464.30 | 1677.15 |
| Mean claims | 1.55 | 1.60 |
| Mean repeated-word fraction | 0.1939 | 0.2045 |

Mean treatment-minus-Base input delta: **-780.65 tokens** (**-33.88%**).
Mean treatment-minus-Base output delta: **-6.50 tokens**.
Paired bootstrap 95% interval: **[-21.95, +9.50] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **-0.127**.
Relative treatment output change: **-4.06%**.
Mean treatment-minus-Base total delta: **-787.15 tokens** (**-31.94%**).
Treatment used fewer/equal/more tokens on **20 / 7 / 13** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
