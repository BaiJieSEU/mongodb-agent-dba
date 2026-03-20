# MongoDB DBA Agent — Docker image
#
# Multi-stage build: copies Node 20 LTS binary from the official Node image
# into a Python 3.11-slim base. No apt repo configuration required.
# Supports linux/amd64 and linux/arm64 (Apple Silicon, AWS Graviton).

# Stage 1: Node 20 LTS — source of node binary and node_modules (npm)
FROM node:20-slim AS node

# Stage 2: Runtime image
FROM python:3.11-slim

# Copy Node binary and npm from the Node image
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules

# Symlink npm so it works from PATH
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

# Install MCP server (pin to same version as local dev)
RUN npm install -g @mongodb-js/mongodb-mcp-server@0.0.3 \
    && npm cache clean --force

# Minimal system deps (curl kept small — only used in healthcheck scripts)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps — base + all optional LLM provider packages so the
# single image works for every deployment (ollama / anthropic / azure / bedrock)
COPY requirements.txt .
RUN pip install --no-cache-dir \
        -r requirements.txt \
        langchain-anthropic \
        langchain-google-vertexai \
        langchain-aws \
        langchain-openai

# Copy application source and config
COPY src/ ./src/
COPY config/ ./config/

# Reports directory — bind-mounted from host in docker-compose.yml
RUN mkdir -p reports

# src/ on PYTHONPATH so `from utils.xxx import` works without prefix
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Default: one-shot health check (writes report to /app/reports/ then exits)
CMD ["python", "src/main_agentic.py", "--health-check"]
