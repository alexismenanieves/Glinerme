FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    MODEL_NAME=fastino/gliner2-base-v1 \
    DEVICE=cpu \
    SCHEMAS_DIR=/app/config/schemas \
    MAX_WORKERS=2 \
    HOST=0.0.0.0 \
    PORT=3131

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY config ./config

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ARG MODEL_NAME=fastino/gliner2-base-v1
RUN python -c "from gliner2 import GLiNER2; GLiNER2.from_pretrained('${MODEL_NAME}')"

EXPOSE 3131

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3131/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3131"]
