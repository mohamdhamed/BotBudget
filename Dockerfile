FROM python:3.12-slim

WORKDIR /app

# Install curl for downloading Tailwind CLI
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Tailwind CSS v3 standalone CLI (no Node.js needed)
RUN curl -sLo /usr/local/bin/tailwindcss \
    https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.17/tailwindcss-linux-x64 \
    && chmod +x /usr/local/bin/tailwindcss

# Download Cairo font woff2 files (Arabic subset) for self-hosting
RUN mkdir -p /tmp/fonts && cd /tmp/fonts && \
    curl -sL "https://fonts.gstatic.com/s/cairo/v28/SLXgc1nY6HkvangtZmpQdkhzfH5lkSs2SgRjCAGMQ1z0hOA-W1Q.woff2" -o cairo-400.woff2 && \
    curl -sL "https://fonts.gstatic.com/s/cairo/v28/SLXgc1nY6HkvangtZmpQdkhzfH5lkSs2SgRjCAGMQ1z0hOA-elU.woff2" -o cairo-700.woff2 && \
    curl -sL "https://fonts.gstatic.com/s/cairo/v28/SLXgc1nY6HkvangtZmpQdkhzfH5lkSs2SgRjCAGMQ1z0hOA-clQ.woff2" -o cairo-800.woff2

# Copy project files (.dockerignore excludes .env, .git, etc.)
COPY . .

# Copy fonts into static directory
RUN mkdir -p dashboard/static/fonts && \
    cp /tmp/fonts/*.woff2 dashboard/static/fonts/

# Build minified Tailwind CSS (only used classes — ~10KB)
RUN tailwindcss -c tailwind.config.js \
    -i dashboard/static/css/input.css \
    -o dashboard/static/css/tailwind.css \
    --minify

# Create exports directory
RUN mkdir -p /app/exports

# Health check - verify the process is running
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "main.py"]
