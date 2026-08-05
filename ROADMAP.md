# AeroRAG-X Roadmap

## Phase 1 — Repository foundation

- [x] Python package with `src/` layout
- [x] Ruff, pytest, mypy, and GitHub Actions
- [x] YAML configuration
- [x] NASA NTRS metadata-search client
- [x] CLI commands
- [ ] Create GitHub repository and merge first pull request

## Phase 2 — Reproducible corpus acquisition

- [ ] Define a narrow initial aerospace topic
- [ ] Download and validate NTRS metadata
- [ ] Resolve public PDF links
- [ ] Create document manifest with checksums
- [ ] Add ASRS CSV import
- [ ] Add dataset card and source limitations

## Phase 3 — Document processing

- [ ] Extract PDF text and page boundaries
- [ ] Detect tables and figures
- [ ] Normalize metadata
- [ ] Implement fixed and semantic chunking
- [ ] Preserve page-level citations

## Phase 4 — Retrieval baselines

- [ ] BM25 baseline
- [ ] Dense embedding baseline
- [ ] Vector database integration
- [ ] Hybrid retrieval
- [ ] Cross-encoder reranking

## Phase 5 — Grounded generation

- [ ] LLM abstraction
- [ ] Citation-enforced prompting
- [ ] Refusal when evidence is insufficient
- [ ] Structured answer schema

## Phase 6 — Evaluation and productization

- [ ] Curated question and relevance set
- [ ] Recall@K, MRR, and NDCG
- [ ] Faithfulness and citation correctness
- [ ] FastAPI and interactive UI
- [ ] Docker image and deployment
- [ ] Demo video and final model card
