#!/bin/bash
# MongoDB DBA Agent — run wrapper
#
# Single cluster (set AGENT_MONGO_CLUSTER in .env):
#   ./run.sh "check my cluster health"
#
# Multiple clusters (set AGENT_MONGO_CLUSTERS as comma-separated list in .env):
#   AGENT_MONGO_CLUSTERS=mongodb+srv://c1.net/,mongodb+srv://c2.net/
#   ./run.sh "check my cluster health"
#   → runs once per cluster, each producing a separate timestamped report

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

# Read AGENT_MONGO_CLUSTERS (plural) from .env if set
CLUSTERS=$(grep -E "^AGENT_MONGO_CLUSTERS=" .env 2>/dev/null | cut -d'=' -f2-)

if [ -z "$CLUSTERS" ]; then
  # Single cluster — use AGENT_MONGO_CLUSTER from .env as-is
  docker compose $PROFILE run --rm agent python src/main_agentic.py "$@"
else
  # Multiple clusters — run once per cluster
  echo "$CLUSTERS" | tr ',' '\n' | while IFS= read -r cluster; do
    cluster=$(echo "$cluster" | xargs)  # trim whitespace
    [ -z "$cluster" ] && continue
    echo ""
    echo "━━━ Cluster: $cluster ━━━"
    AGENT_MONGO_CLUSTER="$cluster" docker compose $PROFILE run --rm agent python src/main_agentic.py "$@"
  done
fi
