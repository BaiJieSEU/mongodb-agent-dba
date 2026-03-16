# MongoDB DBA Agent — Product Backlog

Updated: 2026-03-16 | Format: Epic → Story → Acceptance criteria

Priority: **P0** = must-have for health-check goal | **P1** = high value | **P2** = medium | **P3** = nice-to-have
Size: **S** < 1 day | **M** 1–3 days | **L** 3–7 days | **XL** > 7 days

---

## Epic 1 — Complete Cluster Health Check (Read-Only Signals)

*Goal: cover all six health-check dimensions defined in REQUIREMENTS.md §2*

---

### BL-001 · Server & connection health tool
**Priority:** P0 | **Size:** M

**Story:** As the agent, I need to read `serverStatus` so a health check can report
on connections, memory, lock wait time, and uptime.

**Signals to collect:**
- `connections.current` / `connections.available`
- `globalLock.currentQueue.total`
- `mem.resident` (MB), `mem.virtual`
- `extra_info.page_faults`
- `uptime` (seconds)
- `version`

**Acceptance criteria:**
- New MCP tool `get_server_status` calls `runCommand({serverStatus: 1})` via MCP
- Agent can answer "is the server under memory pressure?" using this data
- Health check report includes a Server Health section
- Values compared to configurable thresholds (connections, page faults)

---

### BL-002 · Replication health tool
**Priority:** P0 | **Size:** M

**Story:** As the agent, I need to read `replSetGetStatus` so a health check can
report on member states, replication lag, and oplog coverage.

**Signals to collect:**
- Member states (PRIMARY / SECONDARY / ARBITER / DOWN)
- Replication lag = `optimeDate[primary]` − `optimeDate[secondary]` per member
- Oplog window: size of `local.oplog.rs` ÷ average write rate

**Acceptance criteria:**
- New MCP tool `get_replication_status` covers all signals above
- Agent flags any secondary with lag > configurable threshold (default 60s)
- Agent flags oplog window < configurable minimum (default 24h)
- Health check report includes a Replication section

---

### BL-003 · Collection storage stats tool
**Priority:** P0 | **Size:** M

**Story:** As the agent, I need per-collection size, document count, and average
document size so a health check can identify oversized collections and guide
capacity planning.

**Signals to collect:**
- `storageSize`, `size` (dataSize), `count`, `avgObjSize` per collection
- `totalIndexSize`
- `wiredTiger.cache.bytes currently in the cache` (if available)

**Acceptance criteria:**
- New MCP tool `get_collection_stats` calls `collStats` via MCP
- Supports iterating all collections in a database
- Health check report includes top-N collections by size
- Agent can answer "which collections are biggest?" without manual input

---

### BL-004 · Index usage statistics tool
**Priority:** P0 | **Size:** M

**Story:** As the agent, I need `$indexStats` output so a health check can identify
unused and underused indexes that should be dropped.

**Signals to collect:**
- Ops count per index since last restart
- Index name, key pattern, size
- Last-used timestamp

**Acceptance criteria:**
- New MCP tool `get_index_stats` runs `$indexStats` aggregation via MCP
- Agent identifies indexes with zero ops since restart
- Health check report lists "candidate indexes to drop" with usage counts
- Agent does not recommend dropping `_id` indexes

---

### BL-005 · Current operations tool
**Priority:** P1 | **Size:** S

**Story:** As the agent, I need `db.currentOp()` so a health check can identify
currently running long operations that are not yet in the profiler.

**Signals to collect:**
- Operations with `secs_running` > configurable threshold (default 5s)
- `op`, `ns`, `query`, `waitingForLock`, `numYields`

**Acceptance criteria:**
- New MCP tool `get_current_operations` calls `currentOp` via MCP
- Agent flags operations blocked by locks separately
- Health check report includes "Currently running slow operations" section
- Works correctly when no long operations are running (empty result)

---

### BL-006 · Profiler configuration check
**Priority:** P1 | **Size:** S

**Story:** As the agent, I need to verify the profiler is enabled and configured
at an appropriate threshold before trusting `system.profile` data.

**Acceptance criteria:**
- Agent calls `db.getProfilingStatus()` at the start of any performance investigation
- Reports warning if profiler is off (level 0)
- Reports warning if `slowms` > 100 (threshold may be too high to catch problems)
- Stores profiler config in the health check report

---

### BL-007 · Duplicate and redundant index detection
**Priority:** P1 | **Size:** S

**Story:** As the agent, I need to compare index key patterns across a collection
to identify duplicates (e.g. `{a:1}` and `{a:1, b:1}` where the first is redundant).

**Acceptance criteria:**
- Derived from existing `collection-indexes` MCP output — no new MCP tool needed
- Agent identifies exact duplicates and left-prefix redundancies
- Health check report lists "redundant indexes" with explanation
- ESR field-order violations flagged with suggested corrected order

---

### BL-008 · Aggregation pipeline analysis
**Priority:** P1 | **Size:** M

**Story:** As the agent, I need to run `explain` on common aggregation patterns
found in the profiler so slow aggregations are diagnosed the same way as find queries.

**Acceptance criteria:**
- `_tool_explain_query` extended to support `aggregate` method alongside `find`
- Agent recognises `op: "command"` with `aggregate` key in profiler output
- Health check report distinguishes slow aggregations from slow finds
- Recommendations include `$match` index coverage and `$sort` / `$group` stage advice

---

## Epic 2 — Scheduling & Automation

*Goal: health checks run automatically on a schedule without human invocation*

---

### BL-010 · Health check pipeline
**Priority:** P0 | **Size:** L

**Story:** As a DBA, I want a single `health_check` command that runs all six
health dimensions in sequence and produces a structured report, so I can call it
both interactively and from a scheduler.

**Acceptance criteria:**
- New `HealthCheckAgent` (or `investigate("run health check")` route) executes tools
  in a fixed, safe order: server → replication → storage → index → profiler → current ops
- Each section produces a severity label: `ok` / `warning` / `critical`
- Structured output: machine-readable JSON + human-readable Rich console report
- Overall cluster health score derived from section severities
- Entire run stored as one `health_check` document in `agent_memory`

---

### BL-011 · Configurable scheduler
**Priority:** P0 | **Size:** L

**Story:** As a DBA, I want to configure a cron schedule in `agent_config.yaml`
so health checks run automatically without me being present.

**Acceptance criteria:**
- `schedule.enabled`, `schedule.cron`, `schedule.report_output` in config
- Scheduler implemented with `APScheduler` or `schedule` library (no external service needed)
- Missed runs (if process was stopped) logged but not retroactively executed
- Scheduler start/stop exposed via CLI: `python src/main_agentic.py --daemon`
- Health check results written to `reports/health_YYYY-MM-DD_HH-MM.json`

---

### BL-012 · Trend comparison in scheduled runs
**Priority:** P1 | **Size:** M

**Story:** As a DBA, I want each scheduled health check to compare its findings
against the previous run so I can see whether the cluster is getting better or worse.

**Acceptance criteria:**
- Agent fetches the most recent prior health check from `agent_memory`
- Report highlights metrics that changed by more than a configurable delta
  (e.g. connection count up 40%, new slow queries on a previously clean collection)
- Trend arrows (↑ ↓ →) in the Rich console report
- New recurring issues (appeared in 3+ consecutive runs) flagged as `PERSISTENT`

---

## Epic 3 — Reporting & Alerting

*Goal: findings reach the right people in a useful format*

---

### BL-020 · Structured health check report format
**Priority:** P0 | **Size:** S

**Story:** As a DBA, I want health check output saved as a versioned JSON file
so I can diff runs, feed them into other tools, or archive them.

**Acceptance criteria:**
- Report schema: `{ run_id, timestamp, cluster_uri, overall_severity, sections: [...], recommendations: [...] }`
- Each section: `{ name, severity, signals: [...], findings: [...] }`
- Each recommendation: `{ priority, collection, action, evidence, confidence }`
- Written to `reports/` directory; older than 90 days auto-purged

---

### BL-021 · Severity thresholds configuration
**Priority:** P0 | **Size:** S

**Story:** As a DBA, I want to configure what constitutes a `warning` vs `critical`
finding so the agent's thresholds match my cluster's normal operating range.

**Acceptance criteria:**
- Thresholds in `agent_config.yaml` under `health_check.thresholds`
- Configurable: `replication_lag_warning_s`, `replication_lag_critical_s`,
  `connection_utilisation_warning_pct`, `slow_query_count_warning`,
  `unused_index_ops_threshold`, `oplog_window_warning_hours`
- Defaults sensible out of the box

---

### BL-022 · Webhook / notification output
**Priority:** P1 | **Size:** M

**Story:** As a DBA, I want health check findings posted to Slack or a webhook
when severity reaches `warning` or `critical`, so I am alerted without polling.

**Acceptance criteria:**
- `schedule.alert_webhook_url` in config (Slack incoming webhook or generic HTTP POST)
- `schedule.alert_on_severity: warning` controls minimum severity to notify
- Payload includes overall severity, top 3 findings, and link to full report file
- No notification sent for `ok` runs unless `schedule.always_notify: true`
- Failed webhook delivery logged and retried once; does not crash the scheduler

---

### BL-023 · Confidence scoring on recommendations
**Priority:** P1 | **Size:** S

**Story:** As a DBA reviewing agent recommendations, I want each recommendation
to carry a confidence level and the evidence behind it so I can triage quickly.

**Acceptance criteria:**
- Every recommendation object includes `confidence: high | medium | low`
- `evidence` field lists the specific signals that drove the recommendation
  (e.g. `"50,000 docs examined, 1 returned, no index on email field"`)
- Low-confidence recommendations marked `[REVIEW]` in the console report
- LLM prompt updated to produce structured recommendations with evidence

---

## Epic 4 — Intelligence Improvements

*Goal: more accurate, consistent, and explainable reasoning*

---

### BL-030 · Structured tool output (typed results)
**Priority:** P0 | **Size:** L

**Story:** As a developer, I want MCP tool results parsed into typed Python
dataclasses before being passed to the LLM so that string-parsing bugs are eliminated
and the LLM receives clean structured JSON.

**Acceptance criteria:**
- Each `_tool_*` method returns a typed dataclass (e.g. `SlowQueryResult`, `IndexStatsResult`)
- LLM receives `json.dumps(dataclass.to_dict())` not raw MCP text blocks
- Parsing errors produce a structured error result, not a silent empty list
- Existing tests pass; new unit tests cover each parser

---

### BL-031 · Automatic tool parameter chaining
**Priority:** P1 | **Size:** M

**Story:** As the agent, after identifying slow queries on a collection I want to
automatically pass that collection name into `check_indexes` and `explain_query`
rather than relying on the LLM to produce the correct parameter on the first pass.

**Acceptance criteria:**
- Post `fetch_slow_queries`, agent code extracts the top offending collection
- That collection name is injected as a parameter override into subsequent steps
- LLM still makes the selection decision; code provides the resolved parameter value
- Reduces investigation steps from 3 blind calls to 3 targeted calls

---

### BL-032 · Configurable LLM backend
**Priority:** P1 | **Size:** M

**Story:** As a developer, I want to switch between a local Ollama model and a
remote Claude / GPT model via config so the agent can use a more capable model
for higher-stakes health check reasoning without changing code.

**Acceptance criteria:**
- `ollama.provider: ollama | claude | openai` in config
- Claude backend uses `anthropic` SDK; OpenAI backend uses `openai` SDK
- All three providers support `classify_intent`, `select_tools`, `generate_response`
- Model name configurable per provider
- Fallback to Ollama if remote provider call fails

---

### BL-033 · ESR index order validation
**Priority:** P2 | **Size:** S

**Story:** As the agent, when recommending a compound index I want to validate and
enforce Equality → Sort → Range field ordering so recommendations follow MongoDB
best practices consistently.

**Acceptance criteria:**
- Dedicated ESR validation function in the agent (pure Python, no LLM needed)
- Applied to every compound index recommendation before it is emitted
- If LLM suggests wrong order, function corrects it and appends a note explaining why
- Unit tests cover common ESR violation patterns

---

## Epic 5 — Write-Capable Tier (Approval-Gated)

*Goal: agent can execute its own recommendations after human approval*

---

### BL-040 · Approval-gated index creation
**Priority:** P2 | **Size:** L

**Story:** As a DBA, after reviewing a recommendation I want to approve index
creation in the CLI so the agent executes it without me having to type the command.

**Acceptance criteria:**
- After generating recommendations, agent prompts `Apply this recommendation? [y/N]`
- On approval, a second `MCPClient` without `--readOnly` executes `createIndex`
- Build index progress reported if `background: false` (MongoDB 8 always foreground)
- Result (success / failure) stored in `agent_memory` alongside the investigation
- If user declines, recommendation marked `deferred` in memory for future reference

---

### BL-041 · Approval-gated profiler configuration
**Priority:** P2 | **Size:** S

**Story:** As a DBA, if the agent detects the profiler is off or threshold is too
high, I want it to offer to fix the configuration with my approval.

**Acceptance criteria:**
- Agent detects `level: 0` or `slowms > 100` during health check (see BL-006)
- Proposes exact `profile` command and asks for approval
- On approval, runs `db.setProfilingLevel()` via non-read-only MCP client
- New profiler status confirmed and stored in report

---

### BL-042 · Approval-gated drop unused index
**Priority:** P3 | **Size:** S

**Story:** As a DBA, I want to drop an unused index with agent assistance after
reviewing the zero-usage evidence.

**Acceptance criteria:**
- Agent lists unused indexes with ops count = 0 (from BL-004)
- Prompts for approval per index (never bulk-drop)
- Executes `dropIndex` via non-read-only MCP client
- Skips `_id` indexes unconditionally

---

## Epic 6 — Operational Infrastructure

*Goal: the system is maintainable, multi-cluster, and accessible to a team*

---

### BL-050 · Multi-cluster support
**Priority:** P1 | **Size:** L

**Story:** As a DBA managing more than one MongoDB cluster, I want to run a health
check against any registered cluster by name so I don't need to edit config files.

**Acceptance criteria:**
- `monitored_clusters` list in config replaces single `monitored_cluster` URI
- Each cluster has a `name`, `uri`, and optional `tags` (e.g. `production`, `staging`)
- CLI accepts `--cluster <name>` flag
- Memory store scoped per cluster URI (investigations tagged with cluster name)
- Health check report header includes cluster name

---

### BL-051 · REST API + Web UI
**Priority:** P2 | **Size:** XL

**Story:** As a team, we want to query the agent and review health check history
via a web interface so multiple people can access findings without SSH access.

**Acceptance criteria:**
- FastAPI backend exposes: `POST /investigate`, `GET /health-checks`, `GET /health-checks/{id}`
- Authentication via API key (configurable)
- Lightweight frontend (React or plain HTML) shows latest health check summary
  and allows drilling into sections and recommendations
- `investigation_history` viewable with trend charts (connection count, slow query count)

---

### BL-052 · Immutable audit trail
**Priority:** P2 | **Size:** S

**Story:** As a DBA, I want every recommendation the agent makes and every write
it executes to be logged immutably so I have a complete record for post-incident review.

**Acceptance criteria:**
- New `audit_log` collection in `agent_memory` (no TTL, append-only)
- Every recommendation emitted writes: `{timestamp, cluster, recommendation, confidence, approved_by}`
- Every write executed (Epic 5) writes: `{timestamp, cluster, command, outcome, approved_by}`
- No update or delete operations on `audit_log`

---

### BL-053 · MongoDB Atlas integration
**Priority:** P3 | **Size:** L

**Story:** As a DBA using Atlas, I want the agent to pull metrics from the Atlas
Data API to supplement profiler data with cloud-level metrics (disk IOPS, Atlas
Advisor recommendations).

**Acceptance criteria:**
- Optional `atlas.public_key`, `atlas.private_key`, `atlas.project_id` in config
- When configured, `get_server_status` supplements local data with Atlas metrics
- Atlas Performance Advisor recommendations surfaced alongside agent recommendations
- Gracefully skips Atlas calls if credentials not configured

---

## Backlog Summary

| ID | Title | Priority | Size | Epic |
|---|---|---|---|---|
| BL-001 | Server & connection health tool | P0 | M | 1 |
| BL-002 | Replication health tool | P0 | M | 1 |
| BL-003 | Collection storage stats tool | P0 | M | 1 |
| BL-004 | Index usage statistics tool | P0 | M | 1 |
| BL-010 | Health check pipeline | P0 | L | 2 |
| BL-011 | Configurable scheduler | P0 | L | 2 |
| BL-020 | Structured report format | P0 | S | 3 |
| BL-021 | Severity thresholds config | P0 | S | 3 |
| BL-030 | Structured tool output (typed) | P0 | L | 4 |
| BL-005 | Current operations tool | P1 | S | 1 |
| BL-006 | Profiler configuration check | P1 | S | 1 |
| BL-007 | Duplicate/redundant index detection | P1 | S | 1 |
| BL-008 | Aggregation pipeline analysis | P1 | M | 1 |
| BL-012 | Trend comparison in scheduled runs | P1 | M | 2 |
| BL-022 | Webhook / notification output | P1 | M | 3 |
| BL-023 | Confidence scoring on recommendations | P1 | S | 3 |
| BL-031 | Automatic tool parameter chaining | P1 | M | 4 |
| BL-032 | Configurable LLM backend | P1 | M | 4 |
| BL-050 | Multi-cluster support | P1 | L | 6 |
| BL-033 | ESR index order validation | P2 | S | 4 |
| BL-040 | Approval-gated index creation | P2 | L | 5 |
| BL-041 | Approval-gated profiler config | P2 | S | 5 |
| BL-051 | REST API + Web UI | P2 | XL | 6 |
| BL-052 | Immutable audit trail | P2 | S | 6 |
| BL-042 | Drop unused index (approval-gated) | P3 | S | 5 |
| BL-053 | MongoDB Atlas integration | P3 | L | 6 |

**P0 total:** 9 items (3L + 4M + 2S) — foundation for the health-check goal
**P1 total:** 10 items — high-value once P0 is in place
**P2–P3 total:** 7 items — important but not blocking
