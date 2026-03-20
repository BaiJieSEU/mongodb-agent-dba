#!/bin/bash
# MongoDB DBA Agent — run wrapper
#
# Usage:
#   ./run.sh "check my cluster health"
#   ./run.sh "why is my database slow"
#   ./run.sh "what indexes does the users collection have"

set -e

if [ -z "$1" ]; then
  echo "Usage: ./run.sh \"your question or instruction\""
  exit 1
fi

# Detect Ollama from .env
PROFILE=""
if grep -q "AGENT_LLM_PROVIDER=ollama" .env 2>/dev/null; then
  PROFILE="--profile ollama"
fi

docker compose $PROFILE run --rm agent python src/main_agentic.py "$@"
