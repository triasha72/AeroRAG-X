# Edge runtime benchmark v0.1

This report records a local inference benchmark for AeroRAG-X using
`Qwen/Qwen3-0.6B` on Apple Silicon. It compares CPU, Metal Performance
Shaders (MPS), precision, and LoRA-adapter configurations using a fixed
structured-generation request.

## Environment

- Host platform: `macOS-26.6.1-arm64-arm-64bit`
- Python: `3.12.13`
- PyTorch: `2.13.0`
- Model: `Qwen/Qwen3-0.6B`
- Warm-up iterations per case: 1
- Measured iterations per case: 3
- Input tokens per measured request: 62
- Maximum generated tokens: 96

Model loading is excluded from the per-request latency measurements. Each
measured request includes device synchronization before and after generation.

## Results

| Case | Device | Dtype | Adapter | Mean latency | P50 latency | P95 latency | Output tok/s |
|---|---|---|---|---:|---:|---:|---:|
| base_cpu_float32 | CPU | float32 | Base | 1189.29 ms | 1187.65 ms | 1194.33 ms | 23.54 |
| base_mps_float32 | MPS | float32 | Base | 1015.00 ms | 1017.41 ms | 1017.90 ms | 27.59 |
| base_mps_float16 | MPS | float16 | Base | 695.43 ms | 694.62 ms | 700.47 ms | 40.26 |
| lora_mps_float16 | MPS | float16 | LoRA | 1146.71 ms | 1146.75 ms | 1149.64 ms | 34.01 |

## Findings

- Base MPS float16 was the fastest tested configuration.
- Compared with base CPU float32, base MPS float16 reduced mean latency by
  approximately 41.5%, from 1189.29 ms to 695.43 ms.
- Base MPS float16 increased output throughput by approximately 71.0%, from
  23.54 to 40.26 output tokens per second.
- Base MPS float32 also improved latency and throughput over CPU float32, but
  float16 delivered the strongest result on this host.
- The LoRA MPS float16 case generated 39 output tokens per request, compared
  with 28 for the base cases. Its raw latency is therefore not a strictly
  identical workload comparison. Its normalized throughput was 34.01 output
  tokens per second.

## Limitations

These results describe one local workload on one Apple Silicon host. They do
not claim Qualcomm QNN, Hexagon, Android, Snapdragon, or other
device-specific deployment performance. They also do not measure low-bit
quantization, memory consumption, model size, quality regression, or
multi-request concurrency.

The next phase will compare an actual low-bit runtime configuration against
the float16 baseline while measuring output quality, latency, throughput, and
artifact size.