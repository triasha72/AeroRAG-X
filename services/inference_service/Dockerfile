FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY services /app/services

RUN pip install --no-cache-dir -e ".[vector,llm,agentic]"

ENV PYTHONPATH=/app:/app/src

CMD ["uvicorn", "services.inference_service.app:app", "--host", "0.0.0.0", "--port", "8002"]
