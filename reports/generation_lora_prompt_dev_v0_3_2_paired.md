# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **7**. Paired provider calls: **6**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean input tokens | 2228.83 | 2168.33 |
| Mean output tokens | 167.17 | 156.83 |
| Mean total tokens | 2396.00 | 2325.17 |
| Mean claims | 1.50 | 1.50 |
| Mean repeated-word fraction | 0.2352 | 0.2306 |

Mean treatment-minus-Base input delta: **-60.50 tokens** (**-2.71%**).
Mean treatment-minus-Base output delta: **-10.33 tokens**.
Paired bootstrap 95% interval: **[-59.50, +33.50] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **-0.161**.
Relative treatment output change: **-6.18%**.
Mean treatment-minus-Base total delta: **-70.83 tokens** (**-2.96%**).
Treatment used fewer/equal/more tokens on **2 / 1 / 3** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
