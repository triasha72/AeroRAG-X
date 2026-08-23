# Distributed framework comparison v0.1

## Why these integrations exist

FSDP and vLLM remain the primary studies. DeepSpeed ZeRO-3, Megatron-LM,
SGLang, and TensorRT-LLM were added as controlled alternatives so the same
workload can expose where framework choices matter. Adding an integration is
not treated as a benchmark win.

## Training matrix

| Framework | Parallelism | Same objective/data | Checkpoint path | Executed result |
|---|---|---|---|---|
| PyTorch FSDP | full parameter/gradient/optimizer sharding | yes | sharded DCP | pending CUDA run |
| DeepSpeed | ZeRO-3 | yes | DeepSpeed partitioned checkpoint | pending CUDA run |
| Megatron-LM | tensor + sequence parallelism | conversion required | Megatron distributed checkpoint | pending CUDA run |

The DeepSpeed treatment uses the same model, assistant-only tokenization,
train/dev files, batch settings, optimizer settings, and seed as FSDP. Megatron
requires a pinned upstream checkout and a separately recorded conversion to its
indexed dataset and tokenizer format; the launcher refuses to run without that
checkout.

## Serving matrix

| Backend | Interface | Retrieval/evidence path | Concurrency study | Executed result |
|---|---|---|---|---|
| Transformers | in-process | unchanged | reference | existing local studies |
| vLLM | OpenAI-compatible | unchanged | 1/8/16/32 + prefix | pending CUDA run |
| SGLang | OpenAI-compatible | unchanged | same harness | pending CUDA run |
| TensorRT-LLM | OpenAI-compatible | unchanged | same harness | pending NVIDIA build/run |

All serving backends return through the same structured response validator.
This controls the RAG pipeline but does not guarantee identical kernels,
tokenizers, quantization, or generated text.

## Decision rule

Choose a framework only after protected quality checks pass. Compare memory,
throughput, latency, TTFT, TPOT, failure rate, checkpoint behavior, restart, and
operational complexity. A faster backend that changes answer validity or cannot
resume reliably does not replace the reference path.

## Current limits

No new GPU numbers are reported here. TensorRT-LLM is restricted to supported
NVIDIA/Linux builds. Megatron data/model conversion is a material part of the
experiment and must be versioned with the run. Multi-node behavior is outside
v0.1.
