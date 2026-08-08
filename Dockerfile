# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    AERORAGX_RUNTIME_MODE=local \
    AERORAGX_CANDIDATE_TOP_K=20 \
    AERORAGX_EVIDENCE_TOP_K=5 \
    HF_HOME=/tmp/huggingface \
    XDG_CACHE_HOME=/tmp/.cache

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

# Install CPU-only PyTorch first so sentence-transformers does not
# resolve the Linux CUDA/NVIDIA dependency stack.
RUN python -m pip install --upgrade pip \
    && python -m pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        torch \
    && python -m pip install .

COPY configs ./configs

# Generated corpus and dense-index artifacts are mounted at runtime.
RUN mkdir -p \
        /app/data/processed \
        /app/artifacts/embeddings \
        /tmp/huggingface \
        /tmp/.cache \
    && chown -R 10001:10001 \
        /app \
        /tmp/huggingface \
        /tmp/.cache

USER 10001:10001

EXPOSE 8000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=300s \
    --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()" || exit 1

CMD ["python", "-m", "uvicorn", "aeroragx.api:app", "--host", "0.0.0.0", "--port", "8000"]
