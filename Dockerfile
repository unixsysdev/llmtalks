FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create workspace directories
RUN mkdir -p agent_a/workspace agent_a/logs \
    agent_b/workspace agent_b/logs \
    agent_c/workspace agent_c/logs \
    agent_d/workspace agent_d/logs \
    shared orchestrator/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["tail", "-f", "/dev/null"]
