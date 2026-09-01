# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean output tokens | 140.89 | 210.89 |
| Mean claims | 1.26 | 2.21 |
| Mean repeated-word fraction | 0.1184 | 0.2748 |

Paired completed queries: **29**. Paired provider calls: **19**.
Mean treatment-minus-Base output delta: **+70.00 tokens**.
Paired bootstrap 95% interval: **[+39.32, +99.90] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **+1.005**.
Relative treatment output change: **+49.68%**.
Treatment used fewer/equal/more tokens on **3 / 0 / 16** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
