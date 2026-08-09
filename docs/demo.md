# Local Demo

## Purpose

`scripts/demo_local.sh` provides a short, reproducible local demonstration of the AeroRAG-X FastAPI service.

It starts the deterministic local runtime, waits for readiness, validates health and readiness endpoints, sends one grounded aerospace query, prints the structured response, and shuts the service down automatically.

## What the demo validates

The demo verifies that the local system can:

- start the FastAPI service;
- load the shared RAG runtime;
- respond successfully to `GET /health`;
- respond successfully to `GET /ready`;
- process `POST /v1/query`;
- return structured claims and authoritative citations;
- shut down without leaving a background server process.

## Prerequisites

Use an environment with AeroRAG-X installed and with the local corpus and embedding artifacts available.

```bash
conda activate aeroragx-py312
```

The demo uses deterministic local mode and does not require an OpenAI API key.

## Run the demo

From the repository root:

```bash
chmod +x scripts/demo_local.sh

bash -n scripts/demo_local.sh

./scripts/demo_local.sh
```

The first run can take up to two minutes while the local runtime loads.

A successful run ends with:

```text
Demo completed successfully.
```

## Optional configuration

The default demo service runs at `http://127.0.0.1:8001`.

Use a different port when needed:

```bash
AERORAGX_DEMO_PORT=8010 ./scripts/demo_local.sh
```

Increase the startup wait limit when running on a slower machine:

```bash
AERORAGX_DEMO_MAX_WAIT_SECONDS=180 ./scripts/demo_local.sh
```

## Demo query

The script uses this development-side query:

```text
How can battery thermal runaway propagate in electric aircraft?
```

It intentionally does not use the protected v0.4 held-out evaluation set.

## Scope and limitations

The demo is an integration walkthrough, not a semantic-quality benchmark. It confirms that the complete local retrieval, sufficiency, generation, citation-resolution, and HTTP path works together.

Benchmark quality, refusal behavior, citation validity, and held-out evaluation results are documented separately in [evaluation.md](evaluation.md).