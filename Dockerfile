# Production Dockerfile for Vocare Restaurant Assistant
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r vocare && useradd -r -g vocare vocare

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp && \
    chown -R vocare:vocare /app

# Switch to non-root user
USER vocare

# Expose ports
EXPOSE 8000 8081

# Add health check using simple port check (doesn't interfere with LiveKit CLI)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python simple_health.py || exit 1

# Use the standard LiveKit CLI command
CMD ["python", "main.py", "start"]

 