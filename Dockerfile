# Multi-stage build: compile with ffmpeg
FROM python:3.11-slim

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run backend with Gunicorn (shell form for $PORT expansion)
# Railway injects PORT env var; defaults to 8000 for local dev
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 120 backend.main:app
