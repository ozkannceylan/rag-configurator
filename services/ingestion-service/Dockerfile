# Ingestion Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package first (from root context)
COPY shared/python /tmp/shared-python
RUN pip install --no-cache-dir /tmp/shared-python && rm -rf /tmp/shared-python

# Copy requirements first for layer caching
COPY services/ingestion-service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/ingestion-service/ .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8002

# Default command (can be overridden for Celery worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
