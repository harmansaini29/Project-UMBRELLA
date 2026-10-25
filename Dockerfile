# ==============================================================================
# PROJECT UMBRELLA: PRODUCTION CONTAINER DOCKERFILE
# Multi-Agent Self-Healing & Evolution System
# ==============================================================================

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (build essentials, sqlite3, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application genome
COPY . .

# Ensure storage directories exist
RUN mkdir -p capsules reports .umbrella_backups

# Expose Mission Control Dashboard (8000) and Target Demo Service (8002)
EXPOSE 8000 8002

# Health check against Mission Control API
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/system/status || exit 1

# Launch Mission Control Platform
CMD ["python", "start_platform.py"]
