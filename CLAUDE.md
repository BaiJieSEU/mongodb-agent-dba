# MongoDB DBA Agent — Development Reference

Agentic AI system for MongoDB DBA tasks. All database operations on the monitored cluster
go through the official MongoDB MCP Server. Agent reasoning and memory run locally via Ollama.

## Environment Setup

### MongoDB Dual-Instance Setup
- **Agent Memory Store**: Port 27017 (rs0) — stores agent investigations and memory
- **Monitored Cluster**: Port 27018 (rs1) — target database under analysis
- **MongoDB Version**: 8.0.4 Community Server
- **Installation Location**: `~/mongodb/`

### Configuration Files
- **Memory Store**: `~/mongodb/config/mongod.conf` (port 27017)
- **Monitored DB**: `~/mongodb/config/mongod2.conf` (port 27018)
- **Agent Config**: `config/agent_config.yaml`

## Development Rules
- Never claim success without running end-to-end tests
- After every change, verify with: `source venv/bin/activate && python src/main_agentic.py "my database is slow"`
- Test memory persistence: run two investigations and confirm the second references the first
- LLM reasoning must drive tool selection — no hardcoded workflows

## Current Implementation (v0.2.0)

### Core Agent
**`src/agent/intelligent_agentic_agent.py`** — `IntelligentAgenticDBAAgent`
- Intent classification via LLM → `DIRECT_ANSWER | DATABASE_METADATA | PERFORMANCE_ANALYSIS | COMPLEX_INVESTIGATION`
- Tool selection via LLM → ordered investigation plan
- All DB operations delegated to `MCPClient` (no direct PyMongo calls to the monitored cluster)
- Memory-aware response synthesis referencing past investigations

### MCP Tool Execution
**`src/utils/mcp_client.py`** — `MCPClient`
- Synchronous context-manager wrapper around `@mongodb-js/mongodb-mcp-server` (stdio)
- Background thread + `asyncio.run()` so anyio cancel scopes stay in one task
- One MCP subprocess per `investigate()` call; closed cleanly on exit
- `--readOnly` flag enforced — no writes to the monitored cluster

MCP operations used:

| Agent method | MCP tool | Notes |
|---|---|---|
| `_tool_list_collections` | `list-collections` | per-database |
| `_tool_list_databases` | `list-databases` | cluster level |
| `_tool_fetch_slow_queries` | `find` on `system.profile` | excludes `getmore`/`killCursors` |
| `_tool_explain_query` | `explain` | find execution plan |
| `_tool_check_indexes` | `collection-indexes` | per-collection |

### Memory System
**`src/memory/agent_memory.py`** — `AgentMemory`
- MongoDB-based persistent storage (port 27017, `agent_memory` database)
- `investigations` collection — full investigation records (TTL 30 days)
- `performance_issues` collection — recurring slow-query tracking (TTL 90 days)
- `user_context` collection — patterns, no TTL
- Upsert logic: `first_detected` lives only in `$setOnInsert`; `detection_count` incremented via `$inc`

## Project Structure

```
mongodb-agent-dba/
├── src/
│   ├── agent/
│   │   └── intelligent_agentic_agent.py  # Core AI agent + MCP dispatch
│   ├── memory/
│   │   ├── __init__.py
│   │   └── agent_memory.py               # MongoDB-based persistent memory
│   ├── models/
│   │   └── query_models.py               # Pydantic data structures
│   ├── utils/
│   │   ├── mcp_client.py                 # Sync wrapper around MongoDB MCP Server
│   │   ├── mongodb_client.py             # Agent store connection (PyMongo)
│   │   └── config_loader.py             # YAML config loader
│   └── main_agentic.py                   # CLI entry point
├── config/
│   └── agent_config.yaml                # Runtime configuration
├── architecture.svg                     # Architecture diagram (dark-mode SVG)
├── architecture_diagram.md              # Architecture narrative
├── CHANGELOG.md                         # Version history
├── REQUIREMENTS.md                      # Product scope and critical analysis
├── requirements.txt                     # Python dependencies (pip)
├── README.md                            # User-facing documentation
├── create_demo_scenario.py              # Generates test data + slow queries
└── CLAUDE.md                           # Development reference (this file)
```

## Testing Protocol

### Prerequisite Check
```bash
# MongoDB instances running
lsof -i :27017   # agent memory store
lsof -i :27018   # monitored cluster

# Ollama
curl http://localhost:11434/api/tags

# MCP Server installed
mongodb-mcp-server --version

# Test data and profiler entries
python3 -c "
import pymongo
client = pymongo.MongoClient('mongodb://localhost:27018/')
db = client['testdb']
print('users:', db.users.count_documents({}))
print('products:', db.products.count_documents({}))
print('slow queries (>=5ms):', db['system.profile'].count_documents({'millis': {'\$gte': 5}}))
"
```

If `system.profile` is empty, regenerate slow queries:
```bash
python create_demo_scenario.py
```

### Test Cases

1. **Metadata question** → MCP `list-collections`:
   ```bash
   source venv/bin/activate && python src/main_agentic.py "how many collections do I have"
   ```
   Expected: agent calls `list_collections`, returns collection count

2. **Performance analysis** → MCP `find` + `collection-indexes` + `explain`:
   ```bash
   python src/main_agentic.py "my database is slow"
   ```
   Expected: agent identifies slow queries on `users`, recommends email index

3. **Memory continuity**:
   ```bash
   python src/main_agentic.py "check slow queries"
   python src/main_agentic.py "is the users collection still slow?"
   ```
   Expected: second response references first investigation

4. **Direct answer** (no DB tools):
   ```bash
   python src/main_agentic.py "what's your name"
   ```
   Expected: `DIRECT_ANSWER` intent, no MCP session opened

## Quick Commands

```bash
# Start both MongoDB instances
export PATH="$HOME/mongodb/bin:$PATH"
mongod --config ~/mongodb/config/mongod.conf          # port 27017
mongod --config ~/mongodb/config/mongod2.conf --fork  # port 27018

# Generate test data + slow profiler entries
source venv/bin/activate && python create_demo_scenario.py

# Run agent
source venv/bin/activate && python src/main_agentic.py "my database is slow"
```

## Troubleshooting

| Symptom | Check |
|---|---|
| Agent won't start | `lsof -i :27017`, `lsof -i :27018`, `curl localhost:11434/api/tags` |
| MCP session timeout | `mongodb-mcp-server --version`; confirm Node 18+ installed |
| No slow queries found | Run `python create_demo_scenario.py`; profiler must be level 1, `slowms≤5` |
| Memory not persisting | Check `agent_memory` database on port 27017; verify TTL indexes exist |
| `first_detected` conflict | Fixed in v0.2.0 — ensure `agent_memory.py` uses `pop()` before upsert |

## Technology Stack

| Layer | Technology |
|---|---|
| LLM reasoning | Ollama + `qwen2.5-coder:7b` |
| DB tool execution | `@mongodb-js/mongodb-mcp-server` (Node 18+) |
| MCP client | Python `mcp` SDK (`mcp[cli]>=1.0.0`) |
| Agent memory store | PyMongo + MongoDB 8.0 (port 27017) |
| CLI / output | Python `rich` |
| Config | PyYAML |
