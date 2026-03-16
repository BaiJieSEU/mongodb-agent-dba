# MongoDB DBA Agent

Agentic AI system for MongoDB database administration that learns from past investigations and provides intelligent, memory-aware recommendations.

## Overview

Natural language interface to your MongoDB cluster. Ask questions like "my database is slow" or "how many collections do I have" — the agent classifies intent, selects tools via the [MongoDB MCP Server](https://github.com/mongodb-js/mongodb-mcp-server), synthesizes findings with memory of past investigations, and responds.

**Key Features**
- **Natural language interface** — understands human queries without rigid syntax
- **LLM-driven tool selection** — no hardcoded workflows; the model decides what to investigate
- **Persistent memory** — learns from past investigations stored in MongoDB (30/90-day TTL)
- **MCP-powered analysis** — database operations delegated to the official MongoDB MCP Server

## Architecture

![Architecture Diagram](architecture.svg)

```
User Query (CLI)
      │
      ▼
main_agentic.py          ← Rich console, arg parsing, prerequisite checks
      │
      ▼
IntelligentAgenticDBAAgent
  ├─ classify_user_intent()     ← LLM: DIRECT_ANSWER | DATABASE_METADATA | PERFORMANCE_ANALYSIS
  ├─ get_investigation_context() ← AgentMemory: past investigations + recurring issues
  ├─ select_tools_intelligently() ← LLM: ordered investigation plan
  ├─ execute_tool()             ← MCPClient → MongoDB MCP Server
  │     ├─ list_collections     → MCP: list-collections
  │     ├─ list_databases       → MCP: list-databases
  │     ├─ fetch_slow_queries   → MCP: find on system.profile
  │     ├─ explain_query        → MCP: explain
  │     └─ check_indexes        → MCP: collection-indexes
  ├─ generate_final_response()  ← LLM: synthesise with memory context
  └─ store_investigation()      ← AgentMemory: persist findings
```

### Infrastructure

| Component | Role | Port |
|---|---|---|
| Ollama + qwen2.5-coder:7b | Local LLM reasoning | 11434 |
| MongoDB MCP Server | Read-only database operations | stdio |
| MongoDB — agent store | Investigation memory (TTL) | 27017 |
| MongoDB — monitored cluster | Target database under analysis | 27018 |

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
pip install langchain-ollama   # required at runtime

# 2. Install MongoDB MCP Server
npm install -g @mongodb-js/mongodb-mcp-server

# 3. Start MongoDB instances
mongod --config ~/mongodb/config/mongod.conf   # agent memory  (27017)
mongod --config ~/mongodb/config/mongod2.conf  # monitored DB  (27018)

# 4. Start Ollama
brew services start ollama
ollama pull qwen2.5-coder:7b

# 5. Generate demo data
python create_demo_scenario.py
```

### Usage

```bash
source venv/bin/activate

python src/main_agentic.py "how many collections do I have"
python src/main_agentic.py "my database is slow"
python src/main_agentic.py "check slow queries"
python src/main_agentic.py "what indexes does my users collection have"
```

## Configuration

`config/agent_config.yaml`:

```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"      # memory storage
  monitored_cluster: "mongodb://localhost:27018" # target database

ollama:
  base_url: "http://localhost:11434"
  model: "qwen2.5-coder:7b"

agent:
  slow_query_threshold_ms: 5
  max_queries_to_analyze: 10
  investigation_timeout: 60
```

## Project Structure

```
src/
├── agent/
│   └── intelligent_agentic_agent.py  # Core AI agent + MCP tool dispatch
├── memory/
│   └── agent_memory.py               # MongoDB-based persistent memory
├── utils/
│   ├── mcp_client.py                 # Sync wrapper around MongoDB MCP Server
│   ├── mongodb_client.py             # Agent store connection
│   └── config_loader.py             # YAML configuration
└── main_agentic.py                   # CLI entry point

config/
└── agent_config.yaml

create_demo_scenario.py               # Loads test data into monitored cluster
```

## Memory System

Investigations are stored in the `agent_memory` database (port 27017):

| Collection | Content | TTL |
|---|---|---|
| `investigations` | Full investigation records | 30 days |
| `performance_issues` | Recurring slow query tracking | 90 days |
| `user_context` | Patterns and preferences | — |

The agent references this history when answering new questions — "I see this collection was slow last week too…"

## MCP Tool Mapping

The agent's logical tools map directly to MongoDB MCP Server operations:

| Agent Tool | MCP Operation | Description |
|---|---|---|
| `list_collections` | `list-collections` | Collections in a database |
| `list_databases` | `list-databases` | All available databases |
| `fetch_slow_queries` | `find` on `system.profile` | Profiler slow query data |
| `explain_query` | `explain` | Query execution plan |
| `check_indexes` | `collection-indexes` | Existing indexes on a collection |

The MCP Server runs in **read-only mode** — no writes to the monitored cluster.

## Scope & Roadmap

See [REQUIREMENTS.md](REQUIREMENTS.md) for a critical analysis of what this system can
and cannot replace (spoiler: it is an AI-augmented DBA tool, not an autonomous DBA),
the task gaps, and the enhancement roadmap.

## License

MIT
