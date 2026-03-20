# MongoDB DBA Agent

AI-augmented MongoDB cluster health monitor. Runs a comprehensive 8-section health
check, produces JSON + HTML reports with prioritised recommendations, and answers
natural language queries — backed by persistent memory that learns from past
investigations.

## Current Capabilities (v0.5.0)

| Health check dimension | Status |
|---|---|
| Cluster overview (databases, collections) | ✅ |
| Server health (startup log, db stats) | ✅ |
| Replication health (oplog window, member state) | ✅ |
| Storage & capacity (data size, index size, growth) | ✅ |
| Query performance (slow queries, scan & sort detection) | ✅ |
| Missing index recommendations | ✅ |
| Unused index detection | ✅ |
| Operations (throughput, memory, cache hit ratio, lock wait) | ✅ |
| LLM-enriched cross-section recommendations | ✅ |
| HTML + JSON report output | ✅ |
| Agentic natural language investigation | ✅ |
| Configurable schedule (daemon mode) | 🔲 BL-011 |

## Quick Start — Docker (recommended)

Requires only Docker and Docker Compose. Pick **one** of the three paths below.

---

### Path A — Anthropic API against a real cluster

Use this when you have an Anthropic API key and want to run against a real MongoDB cluster.

```bash
git clone https://github.com/BaiJieSEU/mongodb-agent-dba
cd mongodb-agent-dba

# .env holds your secrets — it is gitignored and never committed
cp .env.example .env
```

Open `.env` and set these two lines:
```
AGENT_ANTHROPIC_API_KEY=sk-ant-...
AGENT_MONGO_CLUSTER=mongodb+srv://user:pass@your-cluster.mongodb.net/
```

Then run:
```bash
docker compose up
open $(ls -t reports/*.html | head -1)
```

---

### Path B — Local Ollama (no data leaves the machine)

Use this when you need data sovereignty or have no cloud API key.
Downloads a ~5 GB model on first run.

```bash
git clone https://github.com/BaiJieSEU/mongodb-agent-dba
cd mongodb-agent-dba
cp .env.example .env
```

Open `.env` and set:
```
AGENT_LLM_PROVIDER=ollama
AGENT_MONGO_CLUSTER=mongodb+srv://user:pass@your-cluster.mongodb.net/
```

Then run:
```bash
docker compose --profile ollama up -d
docker exec -it ollama ollama pull qwen3:8b   # first run only — ~5 GB download
docker compose --profile ollama run --rm agent
open $(ls -t reports/*.html | head -1)
```

---

### Path C — Full local demo (no cluster, no API key)

Use this to try the agent locally with a built-in demo MongoDB cluster.
Everything runs on your machine; no external services required.

```bash
git clone https://github.com/BaiJieSEU/mongodb-agent-dba
cd mongodb-agent-dba
cp .env.example .env
```

Open `.env` and set:
```
AGENT_LLM_PROVIDER=ollama
```
(`AGENT_MONGO_CLUSTER` can be left unset — the demo cluster starts automatically.)

Then run:
```bash
docker compose --profile ollama --profile demo up -d
docker exec -it ollama ollama pull qwen3:8b         # first run only — ~5 GB download
# Seed the demo cluster with slow queries (first run only):
docker compose --profile ollama --profile demo run --rm agent python create_demo_scenario.py
# Run the health check:
docker compose --profile ollama --profile demo run --rm agent
open $(ls -t reports/*.html | head -1)
```

## Quick Start — Local (manual install)

```bash
# Prerequisites: Python 3.10+, Node 18+, MongoDB 8.0+, Ollama
git clone https://github.com/BaiJieSEU/mongodb-agent-dba
cd mongodb-agent-dba
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm install -g @mongodb-js/mongodb-mcp-server

# Start MongoDB instances (agent memory store + monitored cluster)
mongod --config ~/mongodb/config/mongod.conf   # port 27017
mongod --config ~/mongodb/config/mongod2.conf  # port 27018

# Start Ollama and pull model
brew services start ollama
ollama pull qwen3:8b

# Generate demo data
python create_demo_scenario.py
```

## Usage

```bash
source venv/bin/activate

# Full cluster health check → reports/health_*.json + reports/health_*.html
python src/main_agentic.py --health-check
open $(ls -t reports/*.html | head -1)

# Natural language investigation
python src/main_agentic.py "my database is slow"
python src/main_agentic.py "what indexes does the users collection have"
python src/main_agentic.py "how many collections do I have"
```

## Configuration

Copy `.env.example` to `.env` and set at minimum:

| Variable | Required | Description |
|---|---|---|
| `AGENT_LLM_PROVIDER` | Yes | `ollama` \| `anthropic` \| `azure_openai` \| `bedrock` |
| `AGENT_MONGO_CLUSTER` | For prod | URI of the monitored cluster |
| `AGENT_ANTHROPIC_API_KEY` | If anthropic | Anthropic API key |
| `AGENT_AZURE_OPENAI_KEY` | If azure | Azure OpenAI key |
| `AWS_ACCESS_KEY_ID` | If bedrock | AWS credentials |

Full `config/agent_config.yaml` schema:

```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"       # agent memory
  monitored_cluster: "mongodb://localhost:27018" # target cluster

llm:
  provider: "ollama"   # override: AGENT_LLM_PROVIDER

  ollama:
    base_url: "http://localhost:11434"
    model: "qwen3:8b"

  anthropic:
    model: "claude-sonnet-4-6"

  azure_openai:
    endpoint: ""
    deployment: ""

  bedrock:
    model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
    region: "us-east-1"

agent:
  slow_query_threshold_ms: 5
  llm_recommendations: true   # LLM cross-section recommendation enrichment
```

All `agent_config.yaml` values can be overridden via `AGENT_*` env vars. See `.env.example`.

## Architecture

Two execution paths share the same config and MongoDB connection layer:

```
python src/main_agentic.py --health-check        → Deterministic 8-section pipeline
python src/main_agentic.py "my db is slow"       → LLM-driven agentic investigation
```

### Health Check Pipeline (deterministic)

```
HealthCheckRunner
  §1 Cluster Overview     → MCP: list-databases, list-collections
  §2 Server Health        → MCP: find on local.startup_log, db-stats
  §3 Replication Health   → MCP: find on local.system.replset, local.oplog.rs
  §4 Storage & Capacity   → MCP: db-stats, collection-storage-size, count
  §5 Query Performance    → MCP: find on system.profile (all discovered DBs)
  §6 Missing Indexes      → MCP: collection-indexes on top slow collections
  §7 Unused Indexes       → MCP: aggregate $indexStats (all DBs)
  §8 Operations           → Direct PyMongo: admin.command("serverStatus")
       ↓
  Rule-based recommendations
       ↓
  LLMRecommender.enrich()   (cross-section insights; fails silently)
       ↓
  reports/health_YYYY-MM-DD_HH-MM-SS.json
  reports/health_YYYY-MM-DD_HH-MM-SS.html
```

### Agentic Path (LLM-driven)

```
IntelligentAgenticDBAAgent
  classify_user_intent()        ← LLM
  get_investigation_context()   ← AgentMemory (past investigations)
  select_tools_intelligently()  ← LLM: ordered tool plan
  execute_tool()                ← MCPClient → MongoDB MCP Server (read-only)
  generate_final_response()     ← LLM + memory context
  store_investigation()         ← AgentMemory (TTL persistence)
```

### Infrastructure

| Component | Role | Port |
|---|---|---|
| MongoDB MCP Server | Read-only cluster tool execution | stdio |
| MongoDB — agent store | Investigation memory (TTL indexes) | 27017 |
| MongoDB — monitored cluster | Target cluster under analysis | 27018 |
| Ollama / Anthropic / Azure / Bedrock | LLM reasoning | 11434 or cloud |

## Project Structure

```
mongodb-agent-dba/
├── src/
│   ├── agent/
│   │   ├── health_check_runner.py        # Deterministic 8-section health check
│   │   ├── llm_recommender.py            # LLM cross-section recommendation enrichment
│   │   └── intelligent_agentic_agent.py  # LLM-driven agentic investigation
│   ├── memory/
│   │   └── agent_memory.py               # MongoDB-backed persistent memory (TTL)
│   ├── models/
│   │   └── health_check_report.py        # Typed report schema
│   └── utils/
│       ├── html_reporter.py              # Self-contained HTML report renderer
│       ├── mcp_client.py                 # Sync MCP client wrapper
│       ├── mongodb_client.py             # Agent store + serverStatus connection
│       ├── config_loader.py              # YAML config + AGENT_* env var overrides
│       └── llm_factory.py               # Multi-provider LLM builder
├── config/
│   └── agent_config.yaml                # Runtime configuration
├── Dockerfile                           # Python 3.11 + Node 20 + MCP server
├── docker-compose.yml                   # Four-service stack with profiles
├── .env.example                         # All configurable env vars (copy to .env)
├── reports/                             # JSON + HTML health check output
├── REQUIREMENTS.md                      # Product scope + capability assessment
├── BACKLOG.md                           # Prioritised roadmap
└── create_demo_scenario.py              # Generates testdb with slow queries
```

## Memory System

Investigations persist in the `agent_memory` database (port 27017):

| Collection | Content | TTL |
|---|---|---|
| `investigations` | Full investigation records | 30 days |
| `performance_issues` | Recurring slow query tracking | 90 days |
| `user_context` | Patterns and preferences | — |

The agentic path references this history in new investigations — "I see this
collection was slow last week too…" — and tracks recurring issues across sessions.

## License

MIT
