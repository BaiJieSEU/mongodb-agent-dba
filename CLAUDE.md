# MongoDB DBA Agent — Development Reference

## Product Goal

> The agent must perform a comprehensive MongoDB cluster health check, produce a
> structured report with findings and recommendations, and run on a configurable schedule.

Current version covers: cluster overview, server health, replication health, storage &
capacity, query performance, missing indexes, unused indexes. Dynamically discovers all
databases in the cluster — no hardcoded database names. JSON + HTML reports produced
on every run. Next P0 items: scheduler (BL-011), baseline-aware severity (BL-021),
typed tool output (BL-030), Docker deployment (BL-070).
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
- After every change to the agentic path: `source venv/bin/activate && python src/main_agentic.py "my database is slow"`
- After every change to the health check path: `source venv/bin/activate && python src/main_agentic.py --health-check`
- LLM reasoning must drive tool selection in the agentic path — no hardcoded if/else workflows
- The health check pipeline (`HealthCheckRunner`) is deterministic — no LLM, fixed section order
- MCP client is read-only; never add direct PyMongo writes to the monitored cluster
- All new health-check signals must go through `HealthCheckRunner` section methods → `MCPClient`
- New signals added to a section must also add a `Signal` to that section's `signals` list

---

## Current Implementation

### Two Execution Paths

```
python src/main_agentic.py "my database is slow"     → Agentic path (LLM-driven)
python src/main_agentic.py --health-check            → Health check path (deterministic)
```

`main_agentic.py` routes to one of the two based on the `--health-check` flag or
keyword detection (`health check`, `cluster health`, etc.).

---

### Path 1 — Agentic Investigation

**`src/agent/intelligent_agentic_agent.py`** — `IntelligentAgenticDBAAgent`

- Intent classification → `DIRECT_ANSWER | DATABASE_METADATA | PERFORMANCE_ANALYSIS | COMPLEX_INVESTIGATION`
- Tool selection → LLM produces an ordered investigation plan with parameters
- Tool execution → all DB calls delegated to `MCPClient`
- Response synthesis → LLM with memory context injected
- Investigation storage → `AgentMemory.store_investigation()` + `store_performance_issue()`

| Agent method | MCP tool | Filter / notes |
|---|---|---|
| `_tool_list_collections` | `list-collections` | per database |
| `_tool_list_databases` | `list-databases` | cluster level |
| `_tool_fetch_slow_queries` | `find` on `system.profile` | excludes `getmore`, `killCursors` |
| `_tool_explain_query` | `explain` | find execution plan |
| `_tool_check_indexes` | `collection-indexes` | per collection |

---

### Path 2 — Deterministic Health Check

**`src/agent/health_check_runner.py`** — `HealthCheckRunner`

No LLM involved. Fixed 7-section pipeline executed in order inside one `MCPClient` session.
Produces a `HealthCheckReport` saved as both JSON and HTML to `reports/`.

| # | Section | MCP tools used | Backlog |
|---|---|---|---|
| 1 | Cluster Overview | `list-databases`, `list-collections` | — |
| 2 | Server Health | `find` on `local.startup_log`, `db-stats` (admin) | BL-001 ✅ |
| 3 | Replication Health | `find` on `local.system.replset`, `local.oplog.rs` | BL-002 ✅ |
| 4 | Storage & Capacity | `db-stats`, `collection-storage-size`, `count` | BL-003 ✅ |
| 5 | Query Performance | `find` on `<db>.system.profile` for **every discovered database** | — |
| 6 | Missing Indexes | `collection-indexes` on top slow collections (any db) | — |
| 7 | Unused Indexes | `aggregate $indexStats` per collection across all databases | BL-004 ✅ |

**Key design invariants:**
- Sections 5–7 iterate `user_dbs` (discovered at runtime via `list-databases`); no database
  name is hardcoded anywhere in the pipeline.
- `_section_query_performance(user_dbs)` — queries `system.profile` in each discovered db.
- `_top_slow_collections(slow_queries)` — returns `[{"db": ..., "collection": ...}]` dicts
  so the database is carried through to §6 without re-discovery.
- `_section_index_usage(user_dbs)` — returns `(ReportSection, List[Dict])` tuple; the second
  element is the structured unused-index list passed directly to `_build_recommendations`.
- `_build_recommendations(slow_queries, sections, unused_indexes)` — consumes structured data;
  no string-parsing of finding lines. Iterates all slow queries per collection to find the
  best representative with extractable filter fields (skips aggregate-only profiler entries).

**MCP availability constraints** (confirmed; no workaround possible via read-only MCP):
- `serverStatus` → not available; workaround: `local.startup_log` + `db-stats`
- `replSetGetStatus` → not available; workaround: `local.system.replset` + `local.oplog.rs`
- Connections, memory (RSS), page faults, per-member replication lag → not obtainable

**Report models** — `src/models/health_check_report.py`:
- `HealthSeverity`: `ok | warning | critical`
- `Signal(name, value, unit, threshold)`
- `ReportSection(name, severity, signals, findings)`
- `Recommendation(priority, collection, action, evidence, confidence)`
- `HealthCheckReport(run_id, timestamp, cluster_uri, overall_severity, sections, recommendations)`
- `worst_severity(severities)` — derives overall from section list

**Markdown report** — `src/utils/markdown_reporter.py`:
- `render_markdown(report) -> str` — standard CommonMark, no external dependencies
- Sections as `##` headings with emoji prefix (✅ ⚠️ ❌); signals as Markdown table;
  recommendations as numbered list with bold action line
- Written alongside JSON and HTML as `reports/health_YYYY-MM-DD_HH-MM-SS.md`

**HTML report** — `src/utils/html_reporter.py`:
- `render_html(report) -> str` — pure Python, zero new dependencies
- Dark-theme self-contained HTML; grouped sidebar nav (Overview / Performance / Reliability /
  Action), overall severity banner, section cards, recommendations table with `createIndex` /
  `dropIndex` scripts
- Placeholder sections for Operations (BL-009) and Connections (BL-013) — marked "NOT AVAILABLE"
- ~10 KB output; written alongside JSON as `reports/health_YYYY-MM-DD_HH-MM-SS.html`

---

### MCP Client

**`src/utils/mcp_client.py`** — `MCPClient`

- Sync context manager; background thread + `asyncio.run()` (anyio compatibility)
- One MCP subprocess per `investigate()` / `run()` call; `--readOnly` enforced
- `call_tool(name, args) → list[str]` (text content blocks from MCP response)

---

### Memory System

**`src/memory/agent_memory.py`** — `AgentMemory`

- `agent_memory` database on port 27017
- `investigations` (TTL 30d), `performance_issues` (TTL 90d), `user_context` (no TTL)
- Upsert rule: `first_detected` in `$setOnInsert` only; `detection_count` via `$inc`
  (both must be popped from `$set` dict before the update — prevents MongoDB path conflict)

---

## What Is Still Missing (P0)

| Gap | Backlog item | Notes |
|---|---|---|
| Scheduler | BL-011 (P0/L) | APScheduler or `schedule` lib; `--daemon` CLI flag |
| Baseline-aware severity | BL-021 (P0/M) | Compare metrics to cluster's own history, not static thresholds |
| Typed tool output | BL-030 (P0/L) | Replace string-parsing with dataclasses; LLM gets clean JSON |
| Docker deployment | BL-070 (P0/L) | `docker compose up` — Python + Node + MongoDB + optional Ollama |
| Env var config (full) | BL-071 (P0/S, partial) | LLM + MongoDB vars done; schedule/threshold vars pending |

---

## Project Structure

```
mongodb-agent-dba/
├── src/
│   ├── agent/
│   │   ├── health_check_runner.py        # Deterministic 7-section health check pipeline
│   │   └── intelligent_agentic_agent.py  # LLM-driven agentic investigation
│   ├── memory/
│   │   ├── __init__.py
│   │   └── agent_memory.py               # MongoDB-based persistent memory
│   ├── models/
│   │   ├── health_check_report.py        # Typed report schema (BL-020)
│   │   └── query_models.py               # Pydantic models (agentic path)
│   ├── utils/
│   │   ├── html_reporter.py              # Self-contained HTML report renderer (BL-060)
│   │   ├── mcp_client.py                 # Sync wrapper around MongoDB MCP Server
│   │   ├── mongodb_client.py             # Agent store connection (PyMongo)
│   │   └── config_loader.py              # YAML config loader
│   └── main_agentic.py                   # CLI entry point; routes to agentic or health check
├── config/
│   └── agent_config.yaml                 # Runtime configuration
├── reports/                              # JSON + HTML health check output (auto-created)
├── architecture.svg                      # Architecture diagram
├── CHANGELOG.md                          # Version history
├── REQUIREMENTS.md                       # Product scope + honest capability assessment
├── BACKLOG.md                            # Prioritised roadmap (35 items, 8 epics)
├── requirements.txt                      # Python dependencies (pip)
├── README.md                             # User-facing documentation
├── create_demo_scenario.py               # Generates testdb (5 colls) + testUATdb (2 colls) with slow queries
└── CLAUDE.md                             # Development reference (this file)
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
print('testdb users:', db.users.count_documents({}))
print('testdb slow queries (>=5ms):', db['system.profile'].count_documents({'millis': {'\$gte': 5}}))
db2 = client['testUATdb']
print('testUATdb inventory:', db2.inventory.count_documents({}))
print('testUATdb slow queries (>=5ms):', db2['system.profile'].count_documents({'millis': {'\$gte': 5}}))
"
```

If `system.profile` is empty, run `python create_demo_scenario.py`.

### Test Cases

1. **Health check** — all 7 sections, JSON + HTML output:
   ```bash
   source venv/bin/activate && python src/main_agentic.py --health-check
   open $(ls -t reports/*.html | head -1)
   ```
   Expected: 7 sections, `reports/health_*.json` and `reports/health_*.html` written

2. **Performance investigation** — should call `fetch_slow_queries` + `check_indexes` + `explain_query`:
   ```bash
   source venv/bin/activate && python src/main_agentic.py "my database is slow"
   ```
   Expected: identifies missing email index on `users`, no errors in log

3. **Metadata query** — should call `list_collections` only:
   ```bash
   python src/main_agentic.py "how many collections do I have"
   ```
   Expected: `DATABASE_METADATA` intent, one MCP tool call

4. **Memory continuity** — second run should reference first:
   ```bash
   python src/main_agentic.py "check slow queries"
   python src/main_agentic.py "is the users collection still slow?"
   ```
   Expected: second response mentions prior investigation date

5. **Direct answer** — no MCP session should open:
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

# Run health check (produces JSON + HTML report)
source venv/bin/activate && python src/main_agentic.py --health-check

# Open latest HTML report
open $(ls -t reports/*.html | head -1)

# Run agentic investigation
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
| LLM returns invalid JSON | Retry; if persistent, switch model in `config/agent_config.yaml` — `qwen3:8b` is the active model |
| HTML report not opening | Run `open $(ls -t reports/*.html | head -1)` from project root |

---

## Technology Stack

| Layer | Technology |
|---|---|
| LLM reasoning | `src/utils/llm_factory.py` — Ollama (default), Anthropic, Azure OpenAI, Bedrock; provider set via `llm.provider` or `AGENT_LLM_PROVIDER` env var |
| DB tool execution | `@mongodb-js/mongodb-mcp-server` (Node 18+), read-only |
| MCP client | Python `mcp` SDK (`mcp[cli]>=1.0.0`) |
| Agent memory store | PyMongo + MongoDB 8.0 (port 27017) |
| Report output | JSON + self-contained HTML (`src/utils/html_reporter.py`) |
| CLI / console output | Python `rich` |
| Config | PyYAML |
