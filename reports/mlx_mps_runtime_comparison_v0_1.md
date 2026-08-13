# MLX 4-bit versus Transformers MPS float16 comparison v0.1

## Environment

- Source model: `Qwen/Qwen3-0.6B`
- Platform: `macOS-26.6.1-arm64-arm-64bit`
- Python: `3.12.13`
- PyTorch: `2.13.0`
- Transformers: `5.14.1`
- mlx: `0.32.0`
- mlx-lm: `0.31.3`

## Controlled workload

- Warm-up iterations per runtime: 1
- Measured iterations per runtime: 3
- Maximum input tokens: 2048
- Maximum new tokens: 96
- Both conditions use the same structured prompt and JSON schema.
- Transformers uses MPS float16 with greedy decoding.
- MLX uses the local affine 4-bit, group-size-128 artifact with deterministic sampling.

## Artifacts

| Runtime | Model identifier | Artifact size | Quantization |
|---|---|---:|---|
| transformers_mps_float16 | `Qwen/Qwen3-0.6B` | 1448.83 MiB | `n/a` |
| mlx_4bit_affine_g128 | `artifacts/models/qwen3_0_6b_mlx_4bit` | 313.10 MiB | `{"bits": 4, "group_size": 128, "mode": "affine"}` |

## Results

| Runtime | Valid JSON | Mean latency | P50 latency | P95 latency | Output tok/s | Total input tokens | Total output tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| transformers_mps_float16 | 3/3 | 715.11 ms | 699.42 ms | 742.58 ms | 39.15 | 186 | 84 |
| mlx_4bit_affine_g128 | 3/3 | 278.43 ms | 277.85 ms | 280.47 ms | 122.11 | 423 | 102 |

## Interpretation limits

- Model construction and loading are excluded from per-request latency.
- MPS and MLX work are synchronized at timing boundaries.
- These are one-host local measurements, not Qualcomm QNN, Hexagon, or device-deployment measurements.
- Latency and throughput do not establish output-quality equivalence; totals are reported across measured iterations.
