# MongoDB DBA Agent — Architecture Documentation

Version: 0.5.0 | Updated: 2026-03-19

## System Overview

Memory-enhanced agentic AI system for MongoDB database administration. Two execution
paths: an LLM-driven agentic investigation path and a deterministic health-check
pipeline that produces structured JSON, HTML, and Markdown reports.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User Interface Layer                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  👤 DBA/Engineer                                                        │
│      │                                                                  │
│      │  "my database is slow"  /  --health-check                       │
│      │                                                                  │
│      ▼                                                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    CLI Interface                                  │  │
│  │                 main_agentic.py                                   │  │
│  │                                                                   │  │
│  │  • Rich console output                                            │  │
│  │  • --health-check flag → deterministic pipeline                  │  │
│  │  • Natural language → agentic investigation                      │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                   │                            │
          (agentic path)              (--health-check path)
                   │                            │
                   ▼                            ▼
┌──────────────────────────┐   ┌────────────────────────────────────────┐
│  AI Agent Intelligence   │   │     Deterministic Health Check          │
│         Layer            │   │            Pipeline                     │
├──────────────────────────┤   ├────────────────────────────────────────┤
│                          │   │                                        │
│  IntelligentAgenticDBA   │   │  HealthCheckRunner                     │
│        Agent             │   │  (health_check_runner.py)              │
│                          │   │                                        │
│  Intent Analysis (LLM)   │   │  Fixed 8-section order:                │
│  Memory Context Lookup   │   │  §1  Cluster Overview                  │
│  Tool Selection  (LLM)   │   │  §2  Server Health                     │
│  Response Synthesis(LLM) │   │  §3  Replication Health                │
│  Investigation Storage   │   │  §4  Storage & Capacity                │
│                          │   │  §5  Query Performance                 │
│  ┌──────────────────────┐ │   │  §6  Index Health                      │
│  │  LLM Factory         │ │   │  §7  Index Usage                       │
│  │  (llm_factory.py)    │ │   │  §8  Operations (serverStatus)         │
│  │                      │ │   │                                        │
│  │  ollama    ✅         │ │   │  No LLM. Rule-based severity.          │
│  │  anthropic ✅         │ │   │  Writes JSON + HTML + Markdown         │
│  │  azure_openai ✅      │ │   │  to reports/ on every run.            │
│  │  bedrock   ✅         │ │   │                                        │
│  └──────────────────────┘ │   └────────────────────────────────────────┘
└──────────────────────────┘                    │
              │                                 │
              └──────────────┬──────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Data Access Layer                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  MCPClient  (src/utils/mcp_client.py)                            │   │
│  │  • Sync wrapper: background thread + asyncio.run()               │   │
│  │  • One MCP subprocess per session; --readOnly enforced           │   │
│  │  • call_tool(name, args) → list[str]                             │   │
│  │                                                                  │   │
│  │  Used for: §1–7 of health check + all agentic tool calls         │   │
│  └──────────────────┬───────────────────────────────────────────────┘   │
│                     │ stdio                                              │
│                     ▼                                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  MongoDB MCP Server  (@mongodb-js/mongodb-mcp-server)            │   │
│  │  --readOnly  --connectionString mongodb://localhost:27018        │   │
│  │                                                                  │   │
│  │  list-databases  list-collections  find  aggregate               │   │
│  │  collection-indexes  collection-storage-size  db-stats  count    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Direct PyMongo — admin.command("serverStatus")                  │   │
│  │  MongoDBManager.get_server_status()                              │   │
│  │  (src/utils/mongodb_client.py)                                   │   │
│  │                                                                  │   │
│  │  Read-only admin command. No writes. Used for §8 Operations:     │   │
│  │  opcounters, memory RSS/virtual, WiredTiger cache stats,         │   │
│  │  lock wait %, query targeting ratio, page faults                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Data Storage Layer                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────┐   │
│  │     Agent Memory Store          │  │     Monitored Cluster       │   │
│  │   MongoDB (localhost:27017)     │  │  MongoDB (localhost:27018)  │   │
│  │                                 │  │                             │   │
│  │  agent_memory database          │  │  testdb                     │   │
│  │  • investigations (TTL:30d)     │  │  • users (~50k docs)        │   │
│  │  • performance_issues (90d)     │  │  • orders (~10k docs)       │   │
│  │  • user_context                 │  │  • products (~5k docs)      │   │
│  │                                 │  │  • system.profile           │   │
│  │                                 │  │                             │   │
│  │                                 │  │  testUATdb                  │   │
│  │                                 │  │  • uat_users (~2k docs)     │   │
│  │                                 │  │  • uat_transactions         │   │
│  └─────────────────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Report Output Layer                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  HealthCheckReport (typed Pydantic model)                               │
│      │                                                                  │
│      ├──▶  JSON      reports/health_YYYY-MM-DD_HH-MM-SS.json           │
│      ├──▶  HTML      reports/health_YYYY-MM-DD_HH-MM-SS.html           │
│      │              (dark-theme, self-contained, zero dependencies)     │
│      └──▶  Markdown  reports/health_YYYY-MM-DD_HH-MM-SS.md             │
│                      (CommonMark; GitHub-renderable)                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agentic Intelligence Components

### LLM Factory (BL-032 ✅)
`src/agent/llm_factory.py` — `build_llm(config: LLMConfig) -> BaseChatModel`

Supports four providers via a single `provider:` key in `agent_config.yaml`:

| Provider | LangChain backend | Notes |
|---|---|---|
| `ollama` | `langchain-ollama` | Default; local; no API key required |
| `anthropic` | `langchain-anthropic` | Requires `ANTHROPIC_API_KEY` |
| `azure_openai` | `langchain-openai` | Requires `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` |
| `bedrock` | `langchain-aws` | Requires AWS credentials |

### Intent Classification
The agent analyzes natural language input to determine investigation strategy:

- **DIRECT_ANSWER**: General questions ("what's your name")
- **DATABASE_METADATA**: Information requests ("how many collections")
- **PERFORMANCE_ANALYSIS**: Performance issues ("database is slow")
- **COMPLEX_INVESTIGATION**: Multi-signal investigations

### Memory System
MongoDB-based persistent learning across investigations:

```
agent_memory (localhost:27017)
├── investigations        # Complete investigation records (TTL: 30 days)
├── performance_issues    # Recurring slow query tracking (TTL: 90 days)
└── user_context         # User preferences and patterns
```

### Dynamic Tool Selection
LLM produces an investigation plan (ordered list of tool calls + parameters) based on:
- User intent classification
- Historical context from memory
- Question complexity analysis

Tools are not hardcoded Python classes — they are logical names that `execute_tool()`
dispatches to the corresponding MongoDB MCP Server operation via `MCPClient`.

## Health Check Pipeline

### Section Pipeline (deterministic — no LLM)

```
HealthCheckRunner.run()
    │
    ├── list-databases (MCP)
    │       → user_dbs list (dynamic, no hardcoded DB names)
    │
    ├── §1  Cluster Overview         list-databases, list-collections (MCP)
    ├── §2  Server Health            local.startup_log, db-stats (MCP)
    ├── §3  Replication Health       local.system.replset, local.oplog.rs (MCP)
    ├── §4  Storage & Capacity       collection-storage-size, count, db-stats (MCP)
    ├── §5  Query Performance        find on system.profile (MCP)
    ├── §6  Index Health             collection-indexes (MCP)
    ├── §7  Index Usage              aggregate $indexStats (MCP)
    └── §8  Operations               admin.command("serverStatus") (Direct PyMongo)
            → opcounters, memory, WiredTiger cache, lock wait, targeting ratio
```

### Dual Data-Access Pattern (§8 Operations)

The health check pipeline uses two data access paths:

**Path A — MCP (§1–7):**
All standard health-check data flows through `MCPClient` → MongoDB MCP Server
with `--readOnly` enforced at the MCP layer. No direct PyMongo connection to the
monitored cluster is used here.

**Path B — Direct PyMongo (§8):**
`serverStatus` is a read-only admin command that is not exposed by the MCP Server's
tool set. `MongoDBManager.get_server_status()` issues `admin.command("serverStatus")`
directly against the monitored cluster. This is a read-only operation — no writes
are made. Every production monitoring tool (Datadog, New Relic, Ops Manager) uses
the same approach.

The `--readOnly` MCP flag guards the MCP tool layer only; it does not prevent a
separate direct connection from issuing read-only admin commands.

### MCP Tool Mapping

| Section | MCP Tools | Notes |
|---|---|---|
| §1 Cluster Overview | `list-databases`, `list-collections` | Dynamic DB discovery |
| §2 Server Health | `find` (local.startup_log), `db-stats` | Version, uptime, disk |
| §3 Replication Health | `find` (local.system.replset, local.oplog.rs) | RS config, oplog window |
| §4 Storage & Capacity | `collection-storage-size`, `count`, `db-stats` | Per-collection + filesystem |
| §5 Query Performance | `find` (system.profile) | Slow queries, scan/sort, targeting |
| §6 Index Health | `collection-indexes` | Missing indexes on slow collections |
| §7 Index Usage | `aggregate` ($indexStats) | Unused index detection |
| §8 Operations | *(direct PyMongo)* | serverStatus — not in MCP toolset |

### MCP Availability Constraints

| Signal | Status | Source |
|---|---|---|
| Slow queries, profiler data | ✅ via MCP | `find` on `system.profile` |
| Collection/DB sizes | ✅ via MCP | `collection-storage-size`, `db-stats` |
| Index inventory | ✅ via MCP | `collection-indexes` |
| Index usage stats | ✅ via MCP | `aggregate $indexStats` |
| Oplog window | ✅ via MCP | `find` on `local.oplog.rs` |
| RS member list | ✅ via MCP | `find` on `local.system.replset` |
| `serverStatus` (ops, memory, cache) | ✅ via direct PyMongo | `admin.command("serverStatus")` |
| Per-member replication lag | ❌ not obtainable | `replSetGetStatus` not in MCP |
| Active connections | ❌ not obtainable | `serverStatus.connections` — covered in BL-013 |

## Report Models

`src/models/health_check_report.py`:

```python
HealthSeverity: ok | warning | critical
Signal(name, value, unit, threshold)
ReportSection(name, severity, signals, findings)
Recommendation(priority, collection, action, evidence, confidence)
HealthCheckReport(run_id, timestamp, cluster_uri, overall_severity, sections, recommendations)
worst_severity(severities)  # ok < warning < critical
```

## Technology Stack

### Core Technologies
- **Python 3.11+**: Application runtime
- **LangChain**: LLM integration framework (multi-provider via `llm_factory.py`)
- **mcp**: Python MCP client SDK (`mcp.ClientSession`, `mcp.client.stdio`)
- **PyMongo**: MongoDB driver — agent memory store (port 27017) + direct serverStatus reads (port 27018)
- **qwen3:8b**: Default local LLM (recommended); `qwen2.5-coder:7b` also supported
- **Rich**: Console output formatting
- **Pydantic v2**: Typed report schema and config models

### Infrastructure
- **MongoDB MCP Server** (`@mongodb-js/mongodb-mcp-server`): §1–7 health-check and all agentic data access
- **Node.js 18+**: Runtime for MongoDB MCP Server
- **MongoDB 8.0+**: Dual-instance setup (memory store on 27017 + monitored cluster on 27018)
- **Ollama** (optional): Local LLM serving; replaceable with Anthropic/Azure/Bedrock via config
- **YAML Configuration**: Flexible system configuration (`config/agent_config.yaml`)

### LLM Configuration
```yaml
llm:
  provider: ollama          # ollama | anthropic | azure_openai | bedrock
  model: qwen3:8b
  base_url: http://localhost:11434  # ollama only
  temperature: 0
```

## Security & Data Flow

### Local-First Design
- **Read-Only by Default**: MCP Server runs with `--readOnly`; direct PyMongo calls are read-only admin commands only
- **No External APIs**: All processing can run fully locally (ollama provider)
- **Data Isolation**: Agent memory (port 27017) and monitored cluster (port 27018) are separate instances
- **No Cloud Dependencies**: Cloud LLM providers are optional, not required

### Data Flow
```
User Input → CLI → [Agentic path: LLM → MCPClient → MCP Server → MongoDB:27018]
                 → [Health check path: HealthCheckRunner
                         → MCPClient (§1–7) → MCP Server → MongoDB:27018
                         → MongoDBManager.get_server_status() (§8) → MongoDB:27018
                    → HealthCheckReport → JSON + HTML + Markdown → reports/]
```

## Configuration Reference

```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"
  monitored_cluster: "mongodb://localhost:27018"

llm:
  provider: ollama
  model: qwen3:8b
  base_url: http://localhost:11434
  temperature: 0

agent:
  slow_query_threshold_ms: 5
  max_queries_to_analyze: 10

memory:
  investigation_ttl_days: 30
  performance_issue_ttl_days: 90
  max_context_investigations: 5
```

## Production Considerations

### Scalability Extensions
- **Scheduler (BL-011)**: APScheduler or `schedule` lib; `--daemon` CLI flag; cron expression in config
- **Docker Deployment (BL-070)**: `docker compose up` — single command startup
- **Env Var Config (BL-071)**: All config overridable via `AGENT_*` env vars
- **Typed Tool Output (BL-030)**: Replace string-parsing with dataclasses; LLM gets clean JSON

### Enterprise Features
- **Role-Based Access**: Authentication and authorization
- **Audit Logging**: Track all agent investigations
- **Alert Integration**: Webhook on severity threshold breach (BL-011 scheduler)
- **Multi-Cluster**: Extend monitored_cluster to an array of URIs

See [REQUIREMENTS.md](REQUIREMENTS.md) for a critical analysis of what the system can
and cannot replace, and the full enhancement roadmap. See [BACKLOG.md](BACKLOG.md) for
the prioritised 35-item roadmap.
