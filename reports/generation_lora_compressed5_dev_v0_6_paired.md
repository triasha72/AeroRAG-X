# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **47**. Paired provider calls: **37**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean input tokens | 2314.43 | 914.08 |
| Mean output tokens | 165.41 | 148.70 |
| Mean total tokens | 2479.84 | 1062.78 |
| Mean claims | 1.62 | 1.35 |
| Mean repeated-word fraction | 0.1999 | 0.1824 |

Mean treatment-minus-Base input delta: **-1400.35 tokens** (**-60.51%**).
Mean treatment-minus-Base output delta: **-16.70 tokens**.
Paired bootstrap 95% interval: **[-39.76, +5.16] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **-0.237**.
Relative treatment output change: **-10.10%**.
Mean treatment-minus-Base total delta: **-1417.05 tokens** (**-57.14%**).
Treatment used fewer/equal/more tokens on **18 / 2 / 17** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
