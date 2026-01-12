# MEB RAG System - Dockerfile
# Multi-stage build for optimized image size

# ===== Stage 1: Builder =====
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for PyMuPDF and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt


# ===== Stage 2: Runtime =====
FROM python:3.11-slim as runtime

# Create non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 -m appuser

WORKDIR /app

# Install runtime dependencies + Turkish font support
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmupdf-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder to appuser's home
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code with proper ownership
COPY --chown=appuser:appuser . .

# Create data directories with proper permissions
RUN mkdir -p /app/data /app/output && \
    chown -R appuser:appuser /app/data /app/output

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
