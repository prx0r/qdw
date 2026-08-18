FROM python:3.13-slim

WORKDIR /app

# Copy dependency spec first for layer caching
COPY pyproject.toml .

# Copy source code
COPY src/ src/
COPY migrations/ migrations/
COPY scripts/ scripts/

# Install (after source is present)
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "qdw.interfaces.api:app", "--host", "0.0.0.0", "--port", "8000"]
