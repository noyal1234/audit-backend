FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY postgres_migrations/ postgres_migrations/
COPY src/ src/
COPY scripts/ scripts/

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONPATH=/app
ENV APP_DEBUG=false

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
