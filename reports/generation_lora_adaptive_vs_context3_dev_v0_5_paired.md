# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **48**. Paired provider calls: **42**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean input tokens | 1518.21 | 1518.21 |
| Mean output tokens | 152.21 | 152.21 |
| Mean total tokens | 1670.43 | 1670.43 |
| Mean claims | 1.60 | 1.60 |
| Mean repeated-word fraction | 0.2002 | 0.2002 |

Mean treatment-minus-Base input delta: **+0.00 tokens** (**+0.00%**).
Mean treatment-minus-Base output delta: **+0.00 tokens**.
Paired bootstrap 95% interval: **[+0.00, +0.00] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **+0.000**.
Relative treatment output change: **+0.00%**.
Mean treatment-minus-Base total delta: **+0.00 tokens** (**+0.00%**).
Treatment used fewer/equal/more tokens on **0 / 42 / 0** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
