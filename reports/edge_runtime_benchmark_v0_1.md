# Edge runtime benchmark v0.1

## Environment

- Model: `Qwen/Qwen3-0.6B`
- Platform: `macOS-26.6.1-arm64-arm-64bit`
- Python: `3.12.13`
- PyTorch: `2.13.0`
- Warm-up iterations per case: 1
- Measured iterations per case: 3

## Results

| Case | Device | Dtype | Adapter | Mean latency | P50 latency | P95 latency | Output tok/s |
|---|---|---|---|---:|---:|---:|---:|
| base_cpu_float32 | cpu | float32 | Base | 1189.29 ms | 1187.65 ms | 1194.33 ms | 23.54 |
| base_mps_float32 | mps | float32 | Base | 1015.00 ms | 1017.41 ms | 1017.90 ms | 27.59 |
| base_mps_float16 | mps | float16 | Base | 695.43 ms | 694.62 ms | 700.47 ms | 40.26 |
| lora_mps_float16 | mps | float16 | LoRA | 1146.71 ms | 1146.75 ms | 1149.64 ms | 34.01 |

## Interpretation

These measurements compare local runtime configurations on one host.
They do not claim Qualcomm QNN, Hexagon, or device-specific deployment performance.
