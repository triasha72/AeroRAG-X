# AeroRAG-X

A production-oriented multimodal retrieval-augmented generation system for aerospace technical knowledge.

## Current milestone

Milestone 1 establishes the repository, configuration, testing, CI, CLI, and NASA NTRS metadata client. It deliberately does **not** add an LLM yet. Reliable ingestion and evaluation come first.

## Planned capabilities

- NASA technical-report and ASRS narrative ingestion
- PDF text, table, and figure extraction
- Semantic chunking and metadata preservation
- Dense and sparse vectorization
- Hybrid retrieval and cross-encoder reranking
- Source-grounded LLM answers with citations
- Multimodal retrieval over report figures
- Retrieval and generation evaluation
- FastAPI service, interactive demo, Docker, and CI/CD

## Local setup on macOS

```bash
conda create -n aeroragx-py312 python=3.12 -y
conda activate aeroragx-py312
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Verify the project

```bash
ruff format .
ruff check .
pytest
mypy src/aeroragx

aeroragx info
aeroragx validate-config
```

## Search NASA NTRS metadata

```bash
aeroragx ntrs-search \
  --title "thermal management electric aircraft" \
  --limit 5
```

Save results:

```bash
aeroragx ntrs-search \
  --title "solid rocket motor" \
  --limit 10 \
  --output data/sample/ntrs_srm_records.json
```

## Repository structure

```text
AeroRAG-X/
├── .github/workflows/ci.yml
├── configs/base.yaml
├── data/sample/
├── docs/
├── src/aeroragx/
│   ├── cli.py
│   ├── config.py
│   └── ingestion/ntrs.py
├── tests/
├── pyproject.toml
└── README.md
```

## Development rules

1. Work on a feature branch.
2. Add or update tests for each behavior.
3. Run Ruff, pytest, and mypy before committing.
4. Never commit large raw PDFs, model weights, secrets, or generated vector indexes.
5. Record data sources, licenses, limitations, and evaluation results.

## Data attribution

Data and metadata retrieved from the NASA Scientific and Technical Information Program should be attributed to NASA STI. ASRS reports are voluntary, de-identified narratives and should not be treated as independently verified facts.
