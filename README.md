# Hi, I’m Triasha Sarkar

### Machine Learning Engineer | Generative AI, Applied ML & Scientific ML

I build machine-learning systems for engineering and scientific problems—from data preparation and model development through rigorous evaluation, deployment-oriented services, and monitoring.

My work spans **evidence-grounded RAG**, **LLM adaptation and evaluation**, **time-series failure detection**, **recommendation systems**, **uncertainty-aware surrogate modeling**, and **ML systems engineering**. My aerospace background gives me a practical perspective on reliability: a model should be accurate, measurable, traceable to its evidence, and clear about when it should not be trusted.

[Portfolio](https://triasha72.github.io/Portfolio/) · [LinkedIn](https://www.linkedin.com/in/triasha-sarkar/) · [Email](mailto:tsarkar34@gatech.edu)

---

## What I Build

| Area                            | Focus                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Generative AI & Retrieval**   | RAG, hybrid retrieval, reranking, grounded generation, citations, LLM adaptation, and evaluation frameworks              |
| **Applied ML & ML Systems**     | Time-series modeling, anomaly detection, recommender systems, APIs, containerized services, CI/CD, and observability     |
| **Scientific ML & Reliability** | Surrogate modeling, uncertainty quantification, simulation failure detection, optimization, and physics-based validation |

---

## Featured Projects

### [AeroRAG-X](https://github.com/triasha72/AeroRAG-X) — Evidence-Grounded RAG for Technical Literature

An independent, deployment-oriented RAG system over public NASA technical literature. It combines BM25 and dense retrieval, Reciprocal Rank Fusion, cross-encoder reranking, pgvector, evidence-sufficiency checks, citation-preserving generation, and structured FastAPI outputs.

* Adapted a local Qwen model with PEFT/LoRA and developed a protected evaluation framework for model and RAG quality.
* Improved conservative semantic concept coverage from **38.2% to 51.3%** and full answer-to-claim capture from **10% to 45%** on the defined evaluation suite.
* Built bounded adaptive retrieval with conditional query rewriting, deterministic termination, provenance-preserving refusal paths, and native plus LangGraph/LangChain orchestration.
* Added Dockerized services, CI/CD, OpenTelemetry/Prometheus observability, local-inference and quantization benchmarks, multimodal retrieval, and versioned evaluation artifacts.

*AeroRAG-X was independently inspired by the HERO coursework grand challenge. It uses public NASA literature only; it does not include or use restricted airline FOQA/ASAP data.*

### [EdgeGenBench](https://github.com/triasha72/EdgeGenBench) — Uncertainty-Aware Scientific ML and Edge Inference

A reproducible benchmark connecting hybrid-electric and hydrogen aircraft design, surrogate modeling, uncertainty estimation, constrained optimization, physics validation, and efficient inference.

* Built a 6,000-sample synthetic aircraft-design benchmark and compared classical models with a multi-output PyTorch surrogate.
* Achieved **0.995 mean held-out test R²** and **99.89% ROC AUC** in the v0.1 baseline suite.
* Added conformal uncertainty, a false-safe-rate-aware feasibility classifier, and a gate that sends risky designs to physics validation.
* Exported and validated ONNX FP32 and dynamically quantized INT8 models; benchmarked model size, P50/P95 latency, and throughput.

### [NewsLens](https://github.com/triasha72/NewsLens) — Leakage-Aware Recommendation, Search, and Serving

An end-to-end ML system using the Microsoft MIND news-recommendation dataset.

* Built a chronological, leakage-aware evaluation pipeline over **5.84M candidate interactions** using Python, SQL, and DuckDB.
* Implemented TF-IDF personalization and a training-only popularity fallback, evaluating NDCG@10, Recall@10, Hit Rate@10, bootstrap confidence intervals, subgroup behavior, and failure modes.
* Served versioned artifacts through FastAPI with readiness checks, tracing, and latency reporting.
* Maintained non-root Docker/Compose images, multi-architecture GitHub Actions builds, and **400+ automated tests**.

---

## Applied Research and Engineering Experience

### Georgia Tech Aerospace Systems Design Laboratory — Graduate Research Assistant

* Built reproducible Python and scikit-learn workflows for M.S. thesis research on failure detection in time-series thrust data.
* Audited a **15,120-case** simulated rocket-motor campaign, identified **6,804** candidate simulator failures, removed duplicate-geometry leakage, and achieved **96.8% accuracy / 0.986 ROC AUC** on unseen geometries.
* Contributed to the Delta Air Lines-sponsored HERO project, developing source-aware retrieval organization for user-led airline safety and risk assessment.
* Built a surrogate of Argonne National Laboratory’s GREET life-cycle model and integrated it with economic and transportation models in a Tableau dashboard delivered to the U.S. Endowment for Forestry & Communities sponsor team.

### Alten India, Embedded at Rolls-Royce — Machine Learning Engineer

* Developed Python-based diagnostic and predictive-maintenance workflows for multivariate aircraft-engine sensor data.
* Ingested JSON, Parquet, HDF5, and CSV data from Azure Blob Storage using Azure Databricks; automated data-quality workflows and engineered 1 Hz/10 Hz time-series features for anomaly detection and component-health risk forecasting.
* Partnered with lifecycle engineers to define failure modes, validate diagnostic signals, and translate model output into actionable maintenance insights.

---

## Technical Stack

**Data & analytics:** Python, SQL/MySQL, C++, MATLAB, pandas, NumPy, SciPy, DuckDB, Azure Blob Storage, Azure Databricks
**Machine learning:** scikit-learn, PyTorch, TensorFlow, Hugging Face Transformers, time-series analysis, anomaly detection, predictive modeling
**GenAI & retrieval:** RAG, pgvector, BM25, dense retrieval, Sentence Transformers, RRF, cross-encoder reranking, grounded generation, PEFT/LoRA
**Scientific ML & evaluation:** surrogate modeling, uncertainty quantification, conformal prediction, constrained multi-objective optimization, held-out evaluation, NDCG/MRR/Recall, ROC AUC, bootstrap confidence intervals
**ML systems & cloud:** FastAPI, REST APIs, Docker/Compose, Google Cloud Run, Cloud Storage, Azure DevOps, ONNX Runtime, Prometheus, OpenTelemetry, GitHub Actions, pytest, Ruff, mypy, CI/CD

---

## Interests

I am pursuing **Machine Learning Engineer, Applied AI Engineer, Applied ML Engineer, Scientific ML Engineer, and ML Research Engineer** opportunities—especially work involving reliable AI systems, retrieval and generative AI, scientific computing, model evaluation, uncertainty, and engineering decision support.
