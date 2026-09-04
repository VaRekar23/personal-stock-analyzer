# StockAI backend — FastAPI (Cloud Run / GKE / VM ready)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

# System deps (build tools for asyncpg/numpy wheels if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# Python deps. emergentintegrations ships from a custom index.
COPY requirements.txt .
RUN pip install --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ -r requirements.txt

# App code
COPY . .

# Cloud Run provides $PORT (default 8080); locally we default to 8001.
ENV PORT=8001
EXPOSE 8001

# Domain layer connects to Postgres/Redis via env (DATABASE_URL/REDIS_URL) and
# degrades gracefully if they are unreachable. Schema is auto-created on startup.
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8001}"]
