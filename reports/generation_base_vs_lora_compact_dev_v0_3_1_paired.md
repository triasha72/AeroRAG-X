# Paired generation-efficiency analysis

Only queries with successful, token-observed provider calls in both conditions are compared.
Refusals and failures are not silently converted into zero-token observations.

Paired completed queries: **5**. Paired provider calls: **4**.

| Metric | Base | Treatment |
|---|---:|---:|
| Mean output tokens | 177.75 | 154.50 |
| Mean claims | 3.25 | 1.75 |
| Mean repeated-word fraction | 0.0948 | 0.1325 |

Mean treatment-minus-Base output delta: **-23.25 tokens**.
Paired bootstrap 95% interval: **[-61.25, +28.50] tokens** (10,000 deterministic resamples).
Paired effect size (Cohen's dz): **-0.448**.
Relative treatment output change: **-13.08%**.
Treatment used fewer/equal/more tokens on **3 / 0 / 1** paired calls.

This is a descriptive paired analysis of the frozen sample, not a population-level significance claim.
