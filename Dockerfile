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

# Run backend directly (no port flags, no shell vars)
# backend/main.py reads PORT from environment (Railway injects it)
# Defaults to 8000 for local development
CMD ["python", "-m", "backend.main"]
