FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ src/
COPY migrations/ migrations/
COPY scripts/ scripts/

EXPOSE 8000

CMD ["uvicorn", "qdw.interfaces.api:app", "--host", "0.0.0.0", "--port", "8000"]
