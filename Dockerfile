
# ---- Stage 1: builder ----
FROM python:3.14-slim AS builder

WORKDIR /app

# OS packages needed to COMPILE dependencies (psycopg2 needs gcc + libpq headers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST: this layer only rebuilds when requirements.txt
# changes, so code edits don't trigger a full dependency reinstall
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Stage 2: runtime ----
FROM python:3.14-slim

WORKDIR /app

# ONLY the runtime library for postgres — not the compile headers, not gcc
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Bring the installed packages over from the builder; build tools stay behind
COPY --from=builder /install /usr/local

# Project source
COPY . .

# Run as non-root: a compromised app process should not own the container
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

CMD ["gunicorn", "sentinel.wsgi:application", "--bind", "0.0.0.0:8000"]