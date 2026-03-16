# MongoDB DBA Agent

Agentic AI system for MongoDB cluster health monitoring. Performs comprehensive,
schedulable cluster health checks and answers natural language queries — backed by
persistent memory that learns from past investigations.

## Product Goal

> Run a complete MongoDB cluster health check automatically on a schedule, produce a
> structured report with findings and recommendations, and store results for trend analysis.

The agent is an **AI-augmented DBA tool** — it owns the observe-and-diagnose loop so
the human DBA can focus on remediation and decisions that require operational context.
See [REQUIREMENTS.md](REQUIREMENTS.md) for the full scope and [BACKLOG.md](BACKLOG.md)
for the prioritised roadmap.

## Current Capabilities (v0.2.0)

| Health check dimension | v0.2.0 | Planned |
|---|---|---|
| Slow query identification | ✅ `system.profile` via MCP | — |
| Query execution plan analysis | ✅ MCP `explain` | aggregation pipelines |
| Index inventory | ✅ MCP `collection-indexes` | usage stats, duplicate detection |
| Database / collection metadata | ✅ MCP `list-*` | storage stats, growth trends |
| Server & connection health | ❌ | `serverStatus` (BL-001) |
| Replication health | ❌ | `replSetGetStatus` (BL-002) |
| Current operations | ❌ | `currentOp` (BL-005) |
| Scheduling | ❌ | configurable cron (BL-011) |
| Structured report output | ❌ | JSON + severity (BL-020) |

## Architecture

![Architecture Diagram](architecture.svg)

```
User Query / Scheduler
        │
        ▼
main_agentic.py          ← Rich console, arg parsing, prerequisite checks
        │
        ▼
IntelligentAgenticDBAAgent
  ├─ classify_user_intent()      ← LLM: DIRECT_ANSWER | DATABASE_METADATA
  │                                        | PERFORMANCE_ANALYSIS | COMPLEX_INVESTIGATION
  ├─ get_investigation_context() ← AgentMemory: past investigations + recurring issues
  ├─ select_tools_intelligently() ← LLM: ordered investigation plan
  ├─ execute_tool()              ← MCPClient → MongoDB MCP Server (read-only)
  │     ├─ list_collections      → MCP: list-collections
  │     ├─ list_databases        → MCP: list-databases
  │     ├─ fetch_slow_queries    → MCP: find on system.profile
  │     ├─ explain_query         → MCP: explain
  │     └─ check_indexes         → MCP: collection-indexes
  ├─ generate_final_response()   ← LLM: synthesise with memory context
  └─ store_investigation()       ← AgentMemory: persist findings + recurring issues
```

### Infrastructure

| Component | Role | Port |
|---|---|---|
| Ollama + qwen2.5-coder:7b | Local LLM reasoning | 11434 |
| MongoDB MCP Server | Read-only cluster operations | stdio |
| MongoDB — agent store | Investigation memory (TTL) | 27017 |
| MongoDB — monitored cluster | Target cluster under analysis | 27018 |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for MongoDB MCP Server)
- MongoDB 8.0+ (two instances)
- Ollama with `qwen2.5-coder:7b`

### Installation

```bash
# 1. Clone and create environment
git clone https://github.com/BaiJieSEU/mongodb-agent-dba
cd mongodb-agent-dba
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Install MongoDB MCP Server
npm install -g @mongodb-js/mongodb-mcp-server

# 3. Start MongoDB instances
mongod --config ~/mongodb/config/mongod.conf   # agent memory  (27017)
mongod --config ~/mongodb/config/mongod2.conf  # monitored DB  (27018)

# 4. Start Ollama
brew services start ollama
ollama pull qwen2.5-coder:7b

# 5. Generate demo data and slow queries
python create_demo_scenario.py
```

### Usage

```bash
source venv/bin/activate

# Performance investigation
python src/main_agentic.py "my database is slow"

# Metadata queries
python src/main_agentic.py "how many collections do I have"
python src/main_agentic.py "what indexes does my users collection have"

# Full health check (currently runs performance + index analysis)
python src/main_agentic.py "run a health check on my cluster"
```

## Configuration

`config/agent_config.yaml`:

```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"       # memory storage
  monitored_cluster: "mongodb://localhost:27018" # target cluster

ollama:
  base_url: "http://localhost:11434"
  model: "qwen2.5-coder:7b"

agent:
  slow_query_threshold_ms: 5
  max_queries_to_analyze: 10
  investigation_timeout: 60

# Coming in BL-011 / BL-021:
# schedule:
#   enabled: true
#   cron: "0 */6 * * *"
#   report_output: file
#   alert_on_severity: warning
#   alert_webhook_url: "https://hooks.slack.com/..."
#
# health_check:
#   thresholds:
#     replication_lag_warning_s: 60
#     connection_utilisation_warning_pct: 80
#     slow_query_count_warning: 10
#     oplog_window_warning_hours: 24
```

## Project Structure

```
mongodb-agent-dba/
├── src/
│   ├── agent/
│   │   └── intelligent_agentic_agent.py  # Core AI agent + MCP tool dispatch
│   ├── memory/
│   │   └── agent_memory.py               # MongoDB-based persistent memory
│   ├── utils/
│   │   ├── mcp_client.py                 # Sync wrapper around MongoDB MCP Server
│   │   ├── mongodb_client.py             # Agent store connection (PyMongo)
│   │   └── config_loader.py             # YAML configuration
│   └── main_agentic.py                   # CLI entry point
├── config/
│   └── agent_config.yaml                # Runtime configuration
├── architecture.svg                     # Architecture diagram
├── CHANGELOG.md                         # Version history
├── REQUIREMENTS.md                      # Product scope and honest capability assessment
├── BACKLOG.md                           # Prioritised roadmap (26 items, 6 epics)
└── create_demo_scenario.py              # Generates test data + slow profiler entries
```

## Memory System

Investigations are stored in the `agent_memory` database (port 27017):

| Collection | Content | TTL |
|---|---|---|
| `investigations` | Full investigation records | 30 days |
| `performance_issues` | Recurring slow query tracking | 90 days |
| `user_context` | Patterns and preferences | — |

The agent references this history in new investigations — "I see this collection was slow
last week too…" — and tracks recurring issues across sessions.

## MCP Tool Mapping

All database operations on the monitored cluster go through the MongoDB MCP Server
in read-only mode. No direct writes to the monitored cluster.

| Agent tool | MCP operation | Purpose |
|---|---|---|
| `list_collections` | `list-collections` | Collections in a database |
| `list_databases` | `list-databases` | All available databases |
| `fetch_slow_queries` | `find` on `system.profile` | Slow query profiler data |
| `explain_query` | `explain` | Query execution plan |
| `check_indexes` | `collection-indexes` | Index inventory per collection |

## License

MIT
