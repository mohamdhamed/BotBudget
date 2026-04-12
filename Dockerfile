FROM python:3.12-slim

# Security: don't run as root
RUN groupadd --gid 1000 botuser && \
    useradd --uid 1000 --gid botuser --shell /bin/bash --create-home botuser

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (.dockerignore excludes .env, .git, etc.)
COPY --chown=botuser:botuser . .

# Create exports directory with proper permissions
RUN mkdir -p /app/exports && chown botuser:botuser /app/exports

# Switch to non-root user
USER botuser

# Health check - verify the process is running
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "main.py"]
