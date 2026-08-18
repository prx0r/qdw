FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QDW_DB=/app/data/qdw.db

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY manifests/ ./manifests/
COPY prompts/ ./prompts/
COPY policies/ ./policies/
COPY attacks/ ./attacks/
COPY acceptance/ ./acceptance/

RUN useradd --create-home --uid 10001 qdw \
    && mkdir -p /app/data /app/.qdw \
    && chown -R qdw:qdw /app

USER qdw

EXPOSE 8000

CMD ["uvicorn","qdw.interfaces.api:app","--host","0.0.0.0","--port","8000"]
