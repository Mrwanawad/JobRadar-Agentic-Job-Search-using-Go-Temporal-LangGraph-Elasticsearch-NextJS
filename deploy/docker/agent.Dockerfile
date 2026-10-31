# Python agent worker: LangGraph agents, Elasticsearch, local embeddings.
# Build context: repo root.
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv \
    FASTEMBED_CACHE_PATH=/app/models PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra platform --no-install-project
# Bake the embedding model into the image: no download at runtime, works offline. It sits
# above the source COPY so code changes reuse this layer instead of re-downloading 130 MB.
# Keep the model name in step with jobradar.agent.search.LocalEmbedder.
RUN /app/.venv/bin/python -c "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/app/models').embed(['warmup']))"
COPY jobradar/ jobradar/
COPY profile.example.yaml README.md ./
RUN uv sync --locked --no-dev --extra platform

RUN useradd --uid 10001 --no-create-home agent && chown -R agent /app/models
USER agent
ENTRYPOINT ["/app/.venv/bin/python", "-m", "jobradar", "worker"]
