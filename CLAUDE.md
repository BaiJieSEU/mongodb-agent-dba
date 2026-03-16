# MongoDB DBA Agent — Development Reference

## Product Goal

> The agent must perform a comprehensive MongoDB cluster health check, produce a
> structured report with findings and recommendations, and run on a configurable schedule.

Current version (v0.2.0) covers query performance and index analysis only.
The P0 backlog items (BL-001 to BL-030) close the gap to a full health check.
See [REQUIREMENTS.md](REQUIREMENTS.md) and [BACKLOG.md](BACKLOG.md).

---

## Environment Setup

### MongoDB Dual-Instance Setup
- **Agent Memory Store**: Port 27017 (rs0) — stores agent investigations and memory
- **Monitored Cluster**: Port 27018 (rs1) — target cluster under analysis
- **MongoDB Version**: 8.0.4 Community Server
- **Installation**: `~/mongodb/`

### Configuration Files
- Memory store: `~/mongodb/config/mongod.conf`
- Monitored cluster: `~/mongodb/config/mongod2.conf`
- Agent config: `config/agent_config.yaml`

---

## Development Rules

- Never claim success without running an end-to-end test
- After every change: `source venv/bin/activate && python src/main_agentic.py "my database is slow"`
- LLM reasoning must drive tool selection — no hardcoded if/else workflows
- MCP client is read-only; never add direct PyMongo writes to the monitored cluster
- All new health-check signals must go through a new `_tool_*` method → MCPClient

---

## Current Implementation (v0.2.0)

### Core Agent
**`src/agent/intelligent_agentic_agent.py`** — `IntelligentAgenticDBAAgent`

- Intent classification → `DIRECT_ANSWER | DATABASE_METADATA | PERFORMANCE_ANALYSIS | COMPLEX_INVESTIGATION`
- Tool selection → LLM produces an ordered investigation plan with parameters
- Tool execution → all DB calls delegated to `MCPClient` (no direct PyMongo to monitored cluster)
- Response synthesis → LLM with memory context injected
- Investigation storage → `AgentMemory.store_investigation()` + `store_performance_issue()`

### MCP Tool Dispatch

| Agent method | MCP tool | Filter / notes |
|---|---|---|
| `_tool_list_collections` | `list-collections` | per database |
| `_tool_list_databases` | `list-databases` | cluster level |
| `_tool_fetch_slow_queries` | `find` on `system.profile` | excludes `getmore`, `killCursors` |
| `_tool_explain_query` | `explain` | find execution plan |
| `_tool_check_indexes` | `collection-indexes` | per collection |

### MCP Client
**`src/utils/mcp_client.py`** — `MCPClient`

- Sync context manager; background thread + `asyncio.run()` (anyio compatibility)
- One MCP subprocess per `investigate()` call; `--readOnly` enforced
- `call_tool(name, args) → list[str]` (text content blocks from MCP response)

### Memory System
**`src/memory/agent_memory.py`** — `AgentMemory`

- `agent_memory` database on port 27017
- `investigations` (TTL 30d), `performance_issues` (TTL 90d), `user_context` (no TTL)
- Upsert rule: `first_detected` in `$setOnInsert` only; `detection_count` via `$inc`
  (both must be popped from `$set` dict before the update — see v0.2.0 bug fix)

---

## What Is Missing for the Health Check Goal

The table below maps REQUIREMENTS.md §2 gaps to backlog items. These are the next
things to build, in priority order.

| Missing signal | Backlog item | How to add |
|---|---|---|
| Server stats (connections, memory, locks) | BL-001 (P0) | New `_tool_get_server_status` → MCP `runCommand serverStatus` |
| Replication lag, member states | BL-002 (P0) | New `_tool_get_replication_status` → MCP `runCommand replSetGetStatus` |
| Collection sizes, storage stats | BL-003 (P0) | New `_tool_get_collection_stats` → MCP `runCommand collStats` |
| Index usage (unused indexes) | BL-004 (P0) | New `_tool_get_index_stats` → MCP `aggregate $indexStats` |
| Health check pipeline | BL-010 (P0) | New `health_check()` method; fixed tool execution order; per-section severity |
| Scheduler | BL-011 (P0) | APScheduler or `schedule` lib; `--daemon` CLI flag |
| Structured JSON report | BL-020 (P0) | Typed report schema; written to `reports/` directory |
| Severity thresholds config | BL-021 (P0) | New `health_check.thresholds` section in `agent_config.yaml` |
| Typed tool output (no string parsing) | BL-030 (P0) | Replace string-split parsing with dataclasses; LLM gets clean JSON |
| Current operations | BL-005 (P1) | New `_tool_get_current_operations` → MCP `runCommand currentOp` |
| Profiler config check | BL-006 (P1) | Read `getProfilingStatus` at investigation start |
| Duplicate/redundant index detection | BL-007 (P1) | Derive from existing `collection-indexes` output |
| Aggregation pipeline analysis | BL-008 (P1) | Extend `_tool_explain_query` to handle `aggregate` op |

---

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
├── REQUIREMENTS.md                      # Product scope + honest capability assessment
├── BACKLOG.md                           # Prioritised roadmap (26 items, 6 epics)
├── requirements.txt                     # Python dependencies (pip)
├── README.md                            # User-facing documentation
├── create_demo_scenario.py              # Generates test data + slow profiler entries
└── CLAUDE.md                           # Development reference (this file)
```

---

## Testing Protocol

### Prerequisite Check
```bash
lsof -i :27017 && lsof -i :27018          # both MongoDB instances running
curl -s http://localhost:11434/api/tags    # Ollama running
mongodb-mcp-server --version              # MCP Server installed

python3 -c "
import pymongo
client = pymongo.MongoClient('mongodb://localhost:27018/')
db = client['testdb']
print('users:', db.users.count_documents({}))
print('slow queries (>=5ms):', db['system.profile'].count_documents({'millis': {'\$gte': 5}}))
"
```

If `system.profile` is empty, run `python create_demo_scenario.py`.

### Test Cases

1. **Performance investigation** — should call `fetch_slow_queries` + `check_indexes` + `explain_query`:
   ```bash
   source venv/bin/activate && python src/main_agentic.py "my database is slow"
   ```
   Expected: identifies missing email index on `users`, no errors in log

2. **Metadata query** — should call `list_collections` only:
   ```bash
   python src/main_agentic.py "how many collections do I have"
   ```
   Expected: `DATABASE_METADATA` intent, one MCP tool call

3. **Memory continuity** — second run should reference first:
   ```bash
   python src/main_agentic.py "check slow queries"
   python src/main_agentic.py "is the users collection still slow?"
   ```
   Expected: second response mentions prior investigation date

4. **Direct answer** — no MCP session should open:
   ```bash
   python src/main_agentic.py "what's your name"
   ```
   Expected: `DIRECT_ANSWER` intent, no MCP log lines

---

## Quick Commands

```bash
# Start both MongoDB instances
export PATH="$HOME/mongodb/bin:$PATH"
mongod --config ~/mongodb/config/mongod.conf           # port 27017
mongod --config ~/mongodb/config/mongod2.conf --fork   # port 27018

# Generate test data + slow profiler entries
source venv/bin/activate && python create_demo_scenario.py

# Run agent
source venv/bin/activate && python src/main_agentic.py "my database is slow"
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Agent won't start | Check `lsof -i :27017`, `lsof -i :27018`, `curl localhost:11434/api/tags` |
| MCP session timeout | Confirm Node 18+ installed; run `mongodb-mcp-server --version` |
| No slow queries found | Run `python create_demo_scenario.py`; profiler must be level 1, `slowms ≤ 5` |
| Memory not persisting | Check `agent_memory` database on port 27017; verify TTL indexes exist |
| `first_detected` conflict | Ensure `agent_memory.py` pops `first_detected` from `$set` before upsert |
| LLM returns invalid JSON | Retry; if persistent, consider switching model (see BL-032) |

---

## Technology Stack

| Layer | Technology |
|---|---|
| LLM reasoning | Ollama + `qwen2.5-coder:7b` (swap via BL-032) |
| DB tool execution | `@mongodb-js/mongodb-mcp-server` (Node 18+), read-only |
| MCP client | Python `mcp` SDK (`mcp[cli]>=1.0.0`) |
| Agent memory store | PyMongo + MongoDB 8.0 (port 27017) |
| CLI / output | Python `rich` |
| Config | PyYAML |
