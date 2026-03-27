# MongoDB DBA Agent — Product Backlog

Updated: 2026-03-19 | Format: Epic → Story → Acceptance criteria

Priority: **P0** = must-have for health-check goal | **P1** = high value | **P2** = medium | **P3** = nice-to-have
Size: **S** < 1 day | **M** 1–3 days | **L** 3–7 days | **XL** > 7 days

---

## Backlog Summary

**Sort order (always): Priority P0 → P1 → P2 → P3, then Size S → M → L → XL within each priority.**
When adding or updating an item, re-insert it in the correct position — do not append to the end.

| ID | Title | Priority | Size | Epic | Status |
|---|---|---|---|---|---|
| BL-020 | Structured report format | P0 | S | 3 | ✅ Done |
| BL-001 | Server & connection health tool | P0 | M | 1 | ✅ Done |
| BL-002 | Replication health tool | P0 | M | 1 | ✅ Done |
| BL-003 | Collection storage stats tool | P0 | M | 1 | ✅ Done |
| BL-004 | Index usage statistics tool | P0 | M | 1 | ✅ Done |
| BL-021 | Baseline-aware severity assessment | P0 | M | 3 | ✅ Done |
| BL-071 | Environment variable + secret config | P0 | S | 8 | 🔶 Partial |
| BL-032 | LangChain multi-LLM backend | P0 | M | 4 | ✅ Done |
| BL-010 | Health check pipeline | P0 | L | 2 | ✅ Done |
| BL-011 | Configurable scheduler | P0 | L | 2 | 🔲 |
| BL-030 | Structured tool output (typed) | P0 | L | 4 | ✅ Done |
| BL-070 | Docker Compose deployment | P0 | L | 8 | ✅ Done |
| BL-009 | Operations health section (serverStatus metrics) | P1 | M | 1 | ✅ Done |
| BL-013 | Connection pool health section | P1 | M | 1 | ✅ Done |
| BL-014 | Scan & sort analysis in Query Performance | P1 | S | 1 | ✅ Done |
| BL-015 | OS / infrastructure metrics (CPU, IOPS, disk queue) | P1 | L | 1 | ✅ Done |
| BL-005 | Current operations tool | P1 | S | 1 | 🔲 |
| BL-006 | Profiler configuration check | P1 | S | 1 | ✅ Done |
| BL-007 | Duplicate/redundant index detection | P1 | S | 1 | ✅ Done |
| BL-023 | Confidence scoring on recommendations | P1 | S | 3 | ✅ Done |
| BL-074 | PS delivery runbook (< 30 min) | P1 | S | 8 | 🔲 |
| BL-078 | Fleet report — scalable cluster navigation | P1 | S | 7 | ✅ Done |
| BL-079 | Sticky cluster identity header in HTML report | P1 | S | 7 | ✅ Done |
| BL-008 | Aggregation pipeline analysis | P1 | M | 1 | 🔲 |
| BL-012 | Trend comparison in scheduled runs | P1 | M | 2 | 🔲 |
| BL-022 | Webhook / notification output | P1 | M | 3 | 🔲 |
| BL-034 | LLM-driven recommendation enrichment (hybrid) | P1 | M | 3 | ✅ Done |
| BL-031 | Automatic tool parameter chaining | P1 | M | 4 | 🔲 |
| BL-060 | HTML report output | P1 | M | 7 | ✅ Done |
| BL-073 | Secret management integration | P1 | M | 8 | 🔲 |
| BL-077 | Credential security best practices | P1 | M | 8 | 🔲 |
| BL-050 | Multi-cluster support | P1 | L | 6 | ✅ Done |
| BL-076 | Multi-cluster unified report | P1 | L | 6 | ✅ Done |
| BL-033 | ESR index order validation | P2 | S | 4 | 🔲 |
| BL-041 | Approval-gated profiler config | P2 | S | 5 | 🔲 |
| BL-052 | Immutable audit trail | P2 | S | 6 | 🔲 |
| BL-081 | HTML report — zero-duplication layout | P1 | S | 7 | ✅ Done |
| BL-082 | HTML report — sidebar & content restructure | P1 | S | 7 | ✅ Done |
| BL-083 | HTML report — collapsible Details panel per section | P1 | S | 7 | 🔲 |
| BL-084 | Metric card tooltips with LLM-contextual explanation | P1 | M | 7 | ✅ Done |
| BL-085 | Query Performance findings — structured readable layout | P1 | S | 7 | 🔲 |
| BL-088 | Score & ticket tiering table in Markdown config | P1 | S | 3 | 🔲 |
| BL-089 | Ticket priority driven by section consequence tier | P1 | S | 3 | 🔲 |
| BL-090 | AI summary, score, and ticket priority alignment | P1 | S | 3 | 🔲 |
| BL-091 | Fleet summary tab for multi-cluster reports | P1 | M | 7 | 🔲 |
| BL-092 | Scoring system audit & simplification | P1 | M | 3 | ✅ Done |
| BL-093 | Slow query threshold: count → % of total queries | P1 | M | 3 | 🔲 |
| BL-086 | Metric tooltip context for non-breached signals (page faults, throughput) | P2 | S | 7 | 🔲 |
| BL-087 | OM version and agent version in report header | P2 | S | 7 | ✅ Done |
| BL-061 | Markdown report output | P2 | S | 7 | ✅ Done |
| BL-075 | Data sovereignty mode | P2 | S | 8 | 🔲 |
| BL-080 | Health rating formula — transparency in report | P2 | S | 7 | ✅ Done |
| BL-072 | Non-Docker quickstart script | P2 | M | 8 | 🔲 |
| BL-040 | Approval-gated index creation | P2 | L | 5 | 🔲 |
| BL-051 | REST API + Web UI | P2 | XL | 6 | 🔲 |
| BL-042 | Drop unused index (approval-gated) | P3 | S | 5 | 🔲 |
| BL-053 | MongoDB Atlas integration | P3 | L | 6 | 🔲 |

**Done:** 29 items (BL-020, BL-001, BL-002, BL-003, BL-004, BL-060, BL-010, BL-032, BL-061, BL-023, BL-014, BL-009, BL-034, BL-070, BL-030, BL-050, BL-076, BL-078, BL-079, BL-080, BL-021, BL-006, BL-007, BL-081, BL-082, BL-084, BL-085, BL-087, BL-092)
**Partial:** 1 item (BL-071 — LLM+MongoDB env vars done, full coverage pending)
**P0:** 1 remaining — scheduler (BL-011)
**P1:** 30 items — high-value once P0 is in place (includes BL-088, BL-089, BL-090, BL-091, BL-093)
**P2–P3:** 9 items — important but not blocking
**Total:** 53 items across 8 epics (28 done, 1 partial, 24 remaining)

---

## Epic 1 — Complete Cluster Health Check (Read-Only Signals)

*Goal: cover all six health-check dimensions defined in REQUIREMENTS.md §2*

---

### BL-009 · Operations health section (serverStatus metrics)
**Priority:** P1 | **Size:** M

**Story:** As a DBA, I want an Operations section in the health check report showing
throughput, CPU, memory, lock wait time, WiredTiger cache stats, and query targeting
ratios so I can spot performance degradation that profiler data alone cannot show.

**Metrics to collect — all from `db.adminCommand("serverStatus")`:**

| Metric | serverStatus path | Why it matters |
|---|---|---|
| Reads/sec, Writes/sec | `opcounters.query / insert / update / delete` | Throughput baseline |
| CPU time | `extra_info.user_time_us` | Process-level CPU burn |
| Memory — RSS | `mem.resident` MB | Actual RAM consumed |
| Memory — virtual | `mem.virtual` MB | Address space, hints at swapping |
| WiredTiger cache used | `wiredTiger.cache["bytes currently in the cache"]` | Cache pressure |
| WiredTiger cache max | `wiredTiger.cache["maximum bytes configured"]` | Capacity ceiling |
| Cache hit ratio | `1 - pages_read_from_disk / pages_requested` | Key health indicator |
| Cache file (disk read ratio) | `pages read into cache / pages requested from the cache` | I/O pressure from cache misses |
| WiredTiger evictions | `wiredTiger.cache["unmodified pages evicted"]` | Eviction pressure |
| Lock wait time | `locks.Global.acquireWaitCount / acquireCount` | Contention indicator |
| Cluster-level query targeting | `metrics.queryExecutor.scanned / scannedObjects` | Index efficiency at cluster scale |
| Cluster-level scan & sort count | `metrics.operation.scanAndOrder` | In-memory sort pressure |
| Page faults | `extra_info.page_faults` | Memory subsystem pressure |
| Getmore rate | `opcounters.getmore` | Cursor-intensive workloads |

**Implementation (Option A — delivered v0.5.0):**
Direct PyMongo `admin.command("serverStatus")` on the monitored cluster — read-only,
no writes. `MongoDBManager.get_server_status()` exposes this; `HealthCheckRunner._section_operations()`
consumes it. The MCP `--readOnly` flag guards only the MCP tool layer; it does not
prevent a separate direct read-only admin command.

**Delivered signals:**
- Throughput: total reads, writes, getmores, commands (cumulative since restart)
- Memory: resident MB, virtual MB
- CPU: user time (sec cumulative), page faults
- WiredTiger: cache used/max MB, hit ratio %, pages evicted
- Lock wait: global lock wait %
- Query targeting: cluster-level scanned keys/objects, ratio per read, scan-and-order count

**Acceptance criteria — met:**
- ✅ Operations section renders in HTML/Markdown/JSON report
- ✅ Removes "NOT AVAILABLE" placeholder for `#sec-ops`
- ✅ Severity WARNING if cache hit ratio < 95% (< 80% = CRITICAL), or lock wait > 5%
- ✅ Severity WARNING if query targeting ratio > 10, CRITICAL if > 100

---

### BL-013 · Connection pool health section
**Priority:** P1 | **Size:** M

**Story:** As a DBA, I want a Connections section showing current vs max connections
and per-client breakdown so I can detect connection leaks and pool exhaustion before
they cause 503s.

**Metrics to collect:**
- Current connections, max connections, available headroom
- Connection creation rate and average connection age
- Per-client service breakdown (if available)
- Connections waiting for a lock

**Blocker:** Connection stats require `db.serverStatus().connections` which is not
accessible via the current read-only MCP interface (same blocker as BL-009).

**Acceptance criteria:**
- Connections section renders in the HTML report between Replication and Storage
- Removes the "NOT AVAILABLE" placeholder for `#sec-connections`
- Signals: `current_connections`, `max_connections`, `connection_utilisation_pct`
- Severity WARNING if utilisation > 70%, CRITICAL if > 90%

---

### BL-014 · Scan & sort analysis in Query Performance (§5)
**Priority:** P1 | **Size:** S

**Story:** As a DBA, I want §5 Query Performance to flag queries that required an
in-memory sort stage or spilled to disk so I can prioritise index changes that
eliminate expensive sort operations.

**Data source:** `system.profile` documents — available via MCP today, no new tooling needed.

| Field | system.profile path | Meaning |
|---|---|---|
| In-memory sort | `hasSortStage: true` | Query sorted in RAM — no index covers the sort |
| Sort spills | `sortSpills: N` | Sort exceeded memory limit, wrote to disk |
| Sort spill bytes | `sortSpillBytes: N` | Volume of disk spill |
| Keys examined | `keysExamined` | Index keys scanned (vs `docsExamined` for documents) |
| Keys-to-docs ratio | `keysExamined / docsExamined` | > 1 suggests multi-key or sparse index overhead |

**Acceptance criteria:**
- §5 findings include a "sort stage" summary: count of slow queries with `hasSortStage: true`
- Sort spills flagged as WARNING (any spill = disk pressure)
- Recommendations include `createIndex({sortField: 1})` for queries with `hasSortStage: true`
  where the sort field is extractable from `query.sort`
- `Signal` added: `queries_with_sort_stage`, `sort_spill_count`

---

### BL-015 · OS / infrastructure metrics (CPU, IOPS, disk queue)
**Priority:** P1 | **Size:** L

**Story:** As a DBA, I want the health check to include OS-level metrics — CPU utilisation,
disk IOPS, and disk queue depth — alongside MongoDB metrics so I can diagnose whether
a performance problem is in MongoDB or in the underlying infrastructure.

**Data sources — outside MongoDB, cannot come from MCP or serverStatus:**

| Metric | Linux source | macOS source | Cloud source |
|---|---|---|---|
| CPU utilisation % | `/proc/stat` or `psutil.cpu_percent()` | `psutil.cpu_percent()` | CloudWatch / Azure Monitor / GCP |
| Disk IOPS (read/write) | `/proc/diskstats` or `psutil.disk_io_counters()` | `psutil.disk_io_counters()` | Cloud provider metrics API |
| Disk queue depth | `/proc/diskstats` (avgqu-sz) | `iostat -x` | Cloud provider metrics API |
| Disk utilisation % | `psutil.disk_usage()` | `psutil.disk_usage()` | Cloud provider metrics API |

**Recommended implementation:** `psutil` Python library — cross-platform (Linux, macOS, Windows),
no external agent required, reads from OS kernel directly. This is the same library used by
MongoDB Ops Manager's host monitoring agent.
Add `psutil>=5.9` to `requirements.txt`. Create `src/utils/os_metrics.py`.

**Note:** These metrics describe the MongoDB **host machine**, not the cluster. For
replica sets, each member needs its own host metrics. For cloud-managed Atlas clusters,
these are not accessible — use Atlas Data API (BL-053) instead.

**Acceptance criteria:**
- New `_section_infrastructure()` in `HealthCheckRunner` collects OS metrics via `psutil`
- Signals: `cpu_utilisation_pct`, `disk_iops_read`, `disk_iops_write`, `disk_queue_depth`
- Severity WARNING if CPU > 80% sustained, disk queue > 2, or IOPS > 80% of provisioned limit
- Gracefully skips if `psutil` not installed (imports guarded with try/except)
- Works on macOS (dev) and Linux (production) — the two target platforms
- Report shows "infrastructure metrics not available" if psutil absent rather than crashing

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

### BL-021 · Baseline-aware severity assessment
**Priority:** P0 | **Size:** M

**Story:** As an agentic DBA, I should determine severity by comparing current
metrics against this cluster's own historical baseline — not against static
thresholds configured by a human. A smart DBA learns what "normal" looks like
for each cluster and flags meaningful deviations.

**Design principles:**
- **Hard safety limits** (universal, coded as constants — not configurable):
  oplog window < 2h → CRITICAL; replication lag > 24h → CRITICAL; disk > 95% → CRITICAL.
  These are always bad regardless of cluster context.
- **Contextual severity** (derived from memory): everything else is judged relative
  to this cluster's own historical baseline. "7 slow queries" is only meaningful
  if the agent knows the cluster normally has 1 or normally has 50.
- **Cold start** (no history yet): apply conservative universal defaults for the
  first 3 runs, then switch to baseline comparison.

**Acceptance criteria:**
- Agent reads prior health check runs from `agent_memory` before assigning severity
- For each metric, computes baseline (rolling average of last N runs) and flags
  deviations > configurable multiplier (e.g. 2×) as WARNING, > 3× as CRITICAL
- Hard safety limits enforced as code constants — never overridden by baseline
- Cold start handled: first 3 runs use conservative defaults, report states
  "baseline not yet established (run N of 3)"
- Report shows both the current value and the baseline: "7 slow queries
  (baseline: 2, 3.5× above normal)"
- The only human-configurable setting is the **alert filter** in `schedule.alert_on_severity`
  (notification threshold) — not the severity logic itself
- **Threshold config (added):** all values in `_THRESHOLDS` dict moved to
  `agent_config.yaml` under a `thresholds:` block so customers can tune them
  to their SLAs without editing code. Code loads from config with the current
  hard-coded values as defaults.

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

### BL-032 · LangChain multi-LLM backend
**Priority:** P0 | **Size:** M

**Story:** As a PS engineer deploying at a customer site, I want to switch the LLM
provider with a single config line so the agent works with whatever the customer
already has — no code changes required.

**Background:**
Customers fall into four deployment patterns, in priority order:
1. **Azure OpenAI** — customer already has Azure; data stays in their Azure tenant
2. **AWS Bedrock (Claude)** — customer on AWS; data stays in their AWS account
3. **Anthropic API** — customer has no cloud commitment; uses API key
4. **Local Ollama + Qwen** — strict data sovereignty; data never leaves the premises

LangChain provides a unified interface for all four without changing business logic.

**Acceptance criteria:**
- `llm.provider` in config: `azure_openai | bedrock | anthropic | ollama`
- Each provider implemented as a LangChain `BaseChatModel` subclass; agent code
  calls only the LangChain interface
- Provider-specific config (endpoint, deployment name, region, model ID) under
  `llm.azure_openai`, `llm.bedrock`, `llm.anthropic`, `llm.ollama` respectively
- All credentials read from environment variables — never from the YAML file
- `classify_intent`, `select_tools`, `generate_response` all work identically
  across providers
- Switching provider requires only changing `llm.provider` in config (or
  `AGENT_LLM_PROVIDER` env var) — zero code changes
- Prerequisite check (`test_prerequisites`) validates the selected provider on startup

---

### BL-030 · Structured tool output (typed results) ✅ Done
**Priority:** P0 | **Size:** L

**Story:** As a developer, I want MCP tool results parsed into typed Python
structures before being passed to the LLM so that string-parsing bugs are eliminated
and the LLM receives clean structured JSON.

**Implemented:** All MCP string-parsing moved into `MCPClient` as typed tool methods.
Callers receive Python-native types (lists, dicts, ints, floats) — no more inline
`b.startswith("Name:")` / `json.loads(block)` / `re.search(...)` scattered across
the codebase.

**New typed methods on `MCPClient`:**
- `list_databases()` → `List[str]`
- `list_collections(db)` → `List[str]`
- `find(db, coll, filter, sort, limit)` → `List[Dict]`
- `db_stats(db)` → `Dict`
- `collection_storage_size(db, coll)` → `float` (MB)
- `count(db, coll, filter)` → `int`
- `aggregate(db, coll, pipeline)` → `List[Dict]`
- `collection_indexes(db, coll)` → `List[Dict]` with `name` and `fields`
- `explain(db, coll, method)` → `str`

`HealthCheckRunner` `_parse_*` static methods removed. `intelligent_agentic_agent.py`
tool handlers updated. `re` import removed from `health_check_runner.py`.

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
**Status:** ✅ Done

**Story:** As a DBA managing more than one MongoDB cluster, I want to run a health
check against any registered cluster by name so I don't need to edit config files.

**Done:**
- `_section_query_performance` iterates all user databases discovered via `list-databases` —
  no database name is hardcoded. Deploy to any cluster; all databases are picked up automatically.
- `_top_slow_collections` returns `{"db", "collection"}` dicts so the correct database is used
  in §6 index checks regardless of which database a slow query came from.
- `monitored_clusters` list in `agent_config.yaml` (name + uri + tags); backward-compat with
  `monitored_cluster` — synthesised into clusters list if the new field is absent.
- `ClusterConfig` model in `config_loader.py`; `MongoDBConfig.get_cluster(name)` lookup helper.
- `AGENT_MONGO_CLUSTERS=uri1,uri2` env var overrides the clusters list (names auto-derived
  from hostnames).
- CLI `--cluster <name>` flag selects which registered cluster to target; defaults to `clusters[0]`.
- `HealthCheckRunner(config, cluster_uri, cluster_name)` — uses the selected URI; report header
  and `HealthCheckReport.cluster_name` field populated.
- `Investigation.cluster_uri` and `PerformanceIssue.cluster_uri` stored in agent memory so
  investigations are scoped per cluster.

---

### BL-076 · Multi-cluster unified report
**Priority:** P1 | **Size:** L

**Story:** As a DBA managing multiple clusters, I want a single report that covers
all clusters so I can review health across my entire fleet without opening a separate
file per cluster.

**Depends on:** BL-050 (multi-cluster run support via `AGENT_MONGO_CLUSTERS`)

**Acceptance criteria:**

**JSON** — top-level envelope wraps N cluster reports:
```json
{
  "run_id": "...",
  "timestamp": "...",
  "cluster_count": 3,
  "overall_severity": "critical",
  "clusters": [
    { "cluster_uri": "...", "overall_severity": "...", "sections": [...], "recommendations": [...] },
    { "cluster_uri": "...", ... },
    { "cluster_uri": "...", ... }
  ]
}
```
Each element of `clusters` is a full existing `HealthCheckReport` object — no changes
to the single-cluster schema.

**Markdown** — single file structured as:
- Summary table at top: cluster | overall severity | critical sections | warning sections
- Full per-cluster content below, each preceded by `# Cluster: <hostname>` and separated by `---`
- Readable as one document; skimmable via headings

**HTML** — single self-contained page:
- Cluster switcher tabs at the top of the page (one tab per cluster, coloured by severity)
- Sidebar nav shows sections for the currently active cluster
- Clicking a tab switches the main content area to that cluster's sections and recommendations
- Overall severity banner updates to reflect the selected cluster
- No page reload — pure CSS/JS tab switching

**Implementation notes:**
- `MultiClusterReport` model wraps `List[HealthCheckReport]` with its own `overall_severity`
  (worst across all clusters) and `run_id`
- `run.sh` collects per-cluster reports and passes them to a new `MultiClusterReporter`
  which produces the unified JSON, MD, and HTML
- Single-cluster path unchanged — `MultiClusterReport` only used when N > 1

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

## Epic 7 — Report Usability

*Goal: health check output is easy to read and share across any platform or OS*

---

### BL-061 · Markdown report output
**Priority:** P2 | **Size:** S

**Story:** As a DBA, I want a Markdown version of the health check report so I can
paste it directly into GitHub issues, Confluence, Notion, or a Slack message without
any formatting conversion.

**Acceptance criteria:**
- `HealthCheckRunner` writes `reports/health_YYYY-MM-DD_HH-MM-SS.md` alongside JSON and HTML
- Uses standard CommonMark — no GitHub-specific extensions required
- Sections rendered as `##` headings with a severity emoji prefix (✅ ⚠️ ❌)
- Signals rendered as a Markdown table
- Recommendations rendered as a numbered list with bold action line
- `--no-markdown` CLI flag to suppress

---

## Epic 8 — Deployment & Distribution

*Goal: a PS engineer can deploy the agent at a customer site in under 30 minutes,
on any machine, regardless of cloud provider or data sovereignty requirement*

---

### BL-071 · Environment variable + secret config
**Priority:** P0 | **Size:** S

**Story:** As a PS engineer, I want every sensitive config value to be driven by
environment variables so no secrets are baked into the image or committed to git,
and so the same image works across all customer environments.

**Acceptance criteria:**
- All config values have a corresponding `AGENT_*` env var that takes precedence over YAML:
  - `AGENT_MONGO_CLUSTER` → `mongodb.monitored_cluster`
  - `AGENT_MONGO_STORE` → `mongodb.agent_store`
  - `AGENT_LLM_PROVIDER` → `llm.provider` (`azure_openai | bedrock | anthropic | ollama`)
  - `AGENT_AZURE_OPENAI_ENDPOINT`, `AGENT_AZURE_OPENAI_KEY`, `AGENT_AZURE_OPENAI_DEPLOYMENT`
  - `AGENT_ANTHROPIC_API_KEY`
  - `AGENT_AWS_REGION`, `AGENT_BEDROCK_MODEL_ID`
  - `AGENT_OLLAMA_URL`, `AGENT_OLLAMA_MODEL`
  - `AGENT_SLOW_QUERY_MS`
- `.env.example` committed to repo with all keys and placeholder values
- `.env` in `.gitignore` — never committed
- `config_loader.py` applies env overrides after loading YAML
- No secrets (API keys, passwords, connection strings) written to YAML or hardcoded anywhere

---

### BL-074 · PS delivery runbook (< 30 min)
**Priority:** P1 | **Size:** S

**Story:** As a PS engineer, I want a step-by-step runbook that takes me from
zero to a running health check at a customer site in under 30 minutes, covering
all four LLM deployment patterns.

**Why this matters:**
The customer only provides two things: a MongoDB connection string and their LLM
choice. The runbook must handle everything else without requiring Python, Node.js,
or Ollama knowledge from the customer.

**Acceptance criteria:**
- `RUNBOOK.md` at repo root: concise numbered steps, no unnecessary prose
- LLM decision tree at the top: Azure OpenAI → Bedrock → Anthropic API → Ollama
- Per-provider env var list with exact variable names and where to find values
- One-command start: `cp .env.example .env && vi .env && docker compose up -d`
- Smoke test command to verify health check produces output within 2 minutes
- Troubleshooting section: top 5 failure modes with exact fix steps
- Estimated time per section: connection config 5 min, LLM config 10 min, verify 5 min

---

### BL-073 · Secret management integration
**Priority:** P1 | **Size:** M

**Story:** As a PS engineer deploying in a production customer environment, I want
the agent to fetch secrets from the customer's existing secret store so no
credentials are stored in `.env` files on disk.

**Providers to support:**
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

**Acceptance criteria:**
- `secret_manager.provider: aws | azure | vault | env` in config (default: `env`)
- `env` provider (current behaviour) reads directly from environment variables
- `aws` provider: fetches JSON secret by ARN; maps keys to agent config
- `azure` provider: fetches secrets from Key Vault by name; maps to agent config
- `vault` provider: fetches from a Vault KV path; maps to agent config
- Provider credentials themselves come from environment variables (IAM role /
  workload identity preferred over static keys)
- Secret fetch happens once at startup; secrets not logged or written to disk
- `AGENT_SECRET_PROVIDER` env var overrides config file setting

---

### BL-077 · Credential security best practices
**Priority:** P1 | **Size:** M

**Story:** As a PS engineer or customer, I want the agent to enforce security best
practices for all credentials it holds — MongoDB connection strings and LLM API keys
— so the deployment meets enterprise security requirements.

**MongoDB connection security:**
- Enforce TLS on all connections: reject `mongodb://` URIs without `tls=true` unless
  explicitly opted out via `AGENT_MONGO_ALLOW_PLAINTEXT=true`
- Validate that the connecting user has only the minimum required roles:
  `read` on monitored databases + `clusterMonitor` on admin — warn if broader roles
  (e.g. `root`, `dbOwner`) are detected via `connectionStatus`
- Log the resolved username and auth mechanism (SCRAM-SHA-256, X.509, IAM) at startup
- Support X.509 certificate auth: `AGENT_MONGO_TLS_CERT` and `AGENT_MONGO_TLS_KEY`
  env vars

**LLM API key security:**
- API keys must never appear in log output — mask all credential values in log lines
- Validate key format at startup and give a clear error before the run begins
  (avoids wasting a full health-check run on a bad key)
- Support short-lived credentials where available:
  - AWS Bedrock: prefer IAM role / instance profile over static access keys
  - GCP Vertex AI: prefer Workload Identity / ADC over service account key files
  - Azure OpenAI: prefer Managed Identity over API keys
- Document the minimum IAM permissions required for each provider in README

**General:**
- `run.sh` warns if `.env` is world-readable (`chmod 600 .env` recommendation)
- Credentials never written to `reports/` output files
- All of the above validated in a `--check-credentials` dry-run mode that exits
  without running the health check

---

### BL-070 · Docker Compose deployment
**Priority:** P0 | **Size:** L

**Story:** As a PS engineer, I want to run `docker compose up` and have the entire
agent stack start automatically so a customer deployment requires no manual
installation of Python, Node.js, Ollama, or MongoDB tooling.

**Why this matters:**
The current setup requires: Python 3.10+, venv, pip, Node 18+, npm, two manually
configured mongod instances, Ollama, and the correct model pulled. That is too many
steps for a 30-minute PS engagement. Docker Compose collapses this to one command.

**Acceptance criteria:**
- `docker-compose.yml` defines three services:
  - `agent` — Python app image; all LLM providers supported via env vars
  - `mongo-memory` — MongoDB 8.0, port 27017, agent memory store
  - `ollama` — profile `ollama` only; skipped when using cloud LLM providers
- `Dockerfile`: Python 3.11-slim + Node 18 + `@mongodb-js/mongodb-mcp-server` + pip deps
- `.env.example` committed; `.env` in `.gitignore`
- `docker compose --profile ollama up` for data-sovereignty deployments;
  `docker compose up` for cloud-LLM deployments (no Ollama container started)
- Health checks for all services; `agent` waits for `mongo-memory` before starting
- `reports/` directory bind-mounted so reports are accessible on the host
- Works on macOS (Apple Silicon + Intel), Linux (amd64 + arm64), Windows (WSL2)

---

### BL-075 · Data sovereignty mode
**Priority:** P2 | **Size:** S

**Story:** As a PS engineer deploying at a customer with strict data residency
requirements, I want explicit documentation and a validated configuration that
guarantees no data leaves the customer's premises.

**Why this matters:**
Customers in regulated industries (finance, healthcare, government) need a written
guarantee and a verifiable configuration — not just an assumption that Ollama is
local.

**Acceptance criteria:**
- `llm.provider: ollama` explicitly documented as the data-sovereignty mode in
  `RUNBOOK.md` and `README.md`
- Startup check: when `AGENT_DATA_SOVEREIGN=true`, agent refuses to start if
  `llm.provider` is not `ollama` — prevents accidental cloud LLM use
- Network egress check: log a warning if any outbound connection is made outside
  the configured MongoDB and Ollama hosts
- `AGENT_DATA_SOVEREIGN` env var documented in `.env.example` with explanation
- Section in `RUNBOOK.md`: "Data Sovereignty Deployment" with Ollama-specific steps

---

### BL-072 · Non-Docker quickstart script
**Priority:** P2 | **Size:** M

**Story:** As a customer without Docker, I want a single setup script that installs
all dependencies and starts the agent so I can get running without reading a long
installation guide.

**Acceptance criteria:**
- `setup.sh` (bash) and `setup.ps1` (PowerShell) cover Linux/macOS and Windows
- Script checks and installs (or reports missing): Python 3.10+, Node 18+, Ollama,
  `@mongodb-js/mongodb-mcp-server`, Python venv + pip deps
- Reads from `.env` if present; prompts for missing required vars
- Ends with a success message and the exact command to run the first health check
- Idempotent — safe to run twice without breaking an existing installation

---

## ✅ Done

Items completed and shipped.

---

### BL-032 · LangChain multi-LLM backend
**Priority:** P0 | **Size:** M | **Epic:** 4

`src/utils/llm_factory.py` — `build_llm(config) -> Runnable[str, str]` factory using LCEL
`llm | StrOutputParser()` so all providers expose a uniform string-in/string-out interface.
Supported providers: `ollama` (default), `anthropic`, `azure_openai`, `bedrock`.
Provider selected by `llm.provider` in `agent_config.yaml` or `AGENT_LLM_PROVIDER` env var.
Credentials only from environment variables — never from YAML.
Optional provider packages (`langchain-anthropic`, `langchain-openai`, `langchain-aws`)
imported lazily with clear error messages if not installed.
`IntelligentAgenticDBAAgent` updated to use `build_llm(config)`. Prerequisites check is now
provider-aware. `.env.example` committed with all variable names and descriptions.

---

### BL-078 · Fleet report — scalable cluster navigation
**Priority:** P1 | **Size:** S | **Epic:** 7

**Story:** As a DBA managing a large fleet, I want the multi-cluster HTML report to
remain navigable when there are 10 or more clusters, so I can switch between them
without the tab bar becoming a cramped horizontal scroller.

**Problem:** The current `cluster-tabs` bar is a flex row with `overflow-x: auto`.
At ~8+ clusters, tab labels are truncated or require horizontal scrolling; the bar
gives no indication that more clusters exist off-screen. The layout breaks further
when cluster names are long (e.g. `prod-eu-west-replica-set-primary`).

**Acceptance criteria:**
- For ≤ 6 clusters: keep the existing horizontal tab bar (no visible change).
- For > 6 clusters: replace the tab bar with a compact dropdown `<select>` or
  a collapsible sidebar list so all cluster names are accessible regardless of count.
- Each entry still carries a severity-coloured dot (OK=green, WARNING=amber, CRITICAL=red).
- Switching clusters is instant (no page reload); current cluster is clearly highlighted.
- No new JS libraries — plain CSS + vanilla JS only.
- Test with a synthetic 10-cluster report to confirm no overflow or clipping.

---

### BL-079 · Sticky cluster identity header in HTML report
**Priority:** P1 | **Size:** S | **Epic:** 7

**Story:** As a DBA reviewing a long health report, I always want to know which
cluster I am looking at without having to scroll back to the top, so I can avoid
acting on the wrong cluster's findings.

**Problem:** In both the single-cluster (`html_reporter.py`) and multi-cluster
(`multi_cluster_html_reporter.py`) HTML reports, the cluster name is only shown
in the `report-header` div at the top of the main pane. Once the user scrolls past
the header, there is no persistent indicator of which cluster is active.

**Acceptance criteria:**
- A sticky bar is rendered at the top of the viewport (CSS `position: sticky; top: 0`)
  and remains visible at all scroll depths.
- The bar shows: cluster name · overall severity badge · run timestamp.
- On the fleet report the bar updates when the user switches clusters (JS).
- The bar must not obscure in-page anchor targets (account for bar height in offset).
- Dark-theme consistent with existing CSS palette; ≤ 32 px tall.
- Applies to both `html_reporter.py` (single-cluster) and `multi_cluster_html_reporter.py`.

---

### BL-080 · Health rating formula — transparency in report
**Priority:** P2 | **Size:** S | **Epic:** 7

**Story:** As a DBA, I want to understand exactly how the Overall Health rating and
the Health Score are calculated, so I can explain the numbers to my team and trust
that the report is not a black box.

**Background — two separate ratings exist today:**

| Rating | Where shown | Formula |
|---|---|---|
| Overall severity | Banner (OK / WARNING / CRITICAL) | `worst_severity()` = `max(section_severities)` — if *any* section is CRITICAL, the cluster is CRITICAL |
| Health score | Sidebar gauge (0–100) | Weighted average: OK=1.0 · WARNING=0.6 · CRITICAL=0.0, averaged across all sections × 100 |

Neither formula is documented or visible anywhere in the generated report. A user
seeing "WARNING · 86 / 100" has no way to know why the banner is WARNING while the
score is 86.

**Acceptance criteria:**
- A small "How is this calculated?" tooltip or collapsible info block is rendered
  immediately below the overall severity banner in both single-cluster and fleet HTML reports.
- The tooltip/block explains in plain English:
  - Overall severity: worst-case — one CRITICAL section makes the whole cluster CRITICAL.
  - Health score: weighted average across all sections (OK=100 pts, WARNING=60 pts, CRITICAL=0 pts).
  - Example: "8 sections · 1 WARNING · 7 OK → score = (7×100 + 1×60) / 8 = 95"
- No new dependencies; pure HTML/CSS inline tooltip or `<details>` element.
- The explanation is also included in the Markdown report as a brief footnote.

---

### BL-061 · Markdown report output
**Priority:** P2 | **Size:** S | **Epic:** 7

`src/utils/markdown_reporter.py` — `render_markdown(report) -> str`. Standard CommonMark.
Sections as `##` headings with severity emoji (✅ ⚠️ ❌). Signals as Markdown table.
Indented findings as blockquotes. Recommendations as numbered list with bold action line.
Written alongside JSON and HTML as `reports/health_YYYY-MM-DD_HH-MM-SS.md`.

---

### BL-023 · Confidence scoring on recommendations
**Priority:** P1 | **Size:** S | **Epic:** 3

`Recommendation.confidence` field (`high | medium | low`) in typed model. `createIndex`
recommendations set `high` when filter fields are extracted from profiler data, `medium`
when they cannot be determined. Drop-index recommendations are `medium`. Displayed in
Rich console, HTML report, and Markdown report.

---

### BL-034 · LLM-driven recommendation enrichment (hybrid)
**Priority:** P1 | **Size:** M | **Epic:** 3

**Story:** As a DBA, I want recommendations that reason across all health check sections
and real observed values — not just two hardcoded rules — so I can act on the most
impactful issues rather than missing signals the rule engine ignores.

**Problem with the current approach:**
`_build_recommendations()` only fires on two rules:
1. Full-scan slow query → `createIndex`
2. Zero-access index → `dropIndex`

Signals collected by the pipeline that never produce recommendations today:
- Cache hit ratio below threshold (§8)
- Lock wait % elevated (§8)
- Page faults detected (§8)
- Oplog window < warning threshold (§3)
- Sort spills to disk (§5)
- Cross-section patterns (e.g. low cache + high targeting + full scans → memory, not just indexes)

**Design — hybrid, not LLM-only:**

```
HealthCheckRunner.run()
    → HealthCheckReport  (deterministic, unchanged)
    → _build_recommendations()      ← keep: fast, obvious, high-confidence rules
    → LLMRecommender.enrich(report) ← NEW: LLM pass over structured report JSON
    → merged + deduplicated list    → report.recommendations
```

The LLM receives the completed `HealthCheckReport` serialised as clean JSON
(section names, severity, signals with values and thresholds, findings text).
It does NOT touch raw MongoDB output — all data collection stays deterministic.

**Prompt contract:**
- Input: `HealthCheckReport` as JSON + system prompt defining `Recommendation` schema
- Output: JSON array of `Recommendation` objects (`priority`, `collection`, `action`, `evidence`, `confidence`)
- Temperature: 0 (deterministic output)
- LLM failure: gracefully skipped — rule-based recommendations still returned

**What the LLM can do that rules cannot:**
- Notice that cache hit ratio is low AND targeting ratio is high → recommend increasing `wiredTigerCacheSizeGB` not just adding indexes
- Spot that oplog window is 2h AND writes are high → flag replication risk
- Prioritise across sections: a CRITICAL cache miss may outrank a WARNING unused index
- Phrase recommendations in natural language matched to the specific observed values

**Acceptance criteria:**
- `LLMRecommender` class in `src/agent/llm_recommender.py`
- Prompt produces valid `Recommendation` JSON; malformed output is caught and skipped
- Rule-based recommendations still generated first (deduplicated by `collection + action`)
- LLM-generated recommendations tagged `confidence: llm` in the model
- Config flag `agent.llm_recommendations: true/false` (default `false` until stable)
- Existing behaviour unchanged when flag is off or LLM unavailable

---

### BL-010 · Health check pipeline
**Priority:** P0 | **Size:** L | **Epic:** 2

`src/agent/health_check_runner.py` — `HealthCheckRunner`. Fixed 7-section pipeline:
Cluster Overview → Server Health → Replication Health → Storage & Capacity →
Query Performance → Missing Indexes → Unused Indexes. Each section produces
`ok / warning / critical` severity; overall severity derived from worst section.
Outputs machine-readable JSON + self-contained HTML to `reports/`. Section names:
"Missing Indexes" (formerly "Index Health") and "Unused Indexes" (formerly "Index Usage").
Note: storing the run in `agent_memory` is deferred to BL-012 (trend comparison).

---

### BL-088 · Score & ticket tiering table in Markdown config
**Priority:** P1 | **Size:** S | **Epic:** 3

**Problem:** The consequence-tier definitions (which section maps to which tier, what the penalty
is, what the tier label is) are hard-coded across `html_reporter.py` and `llm_recommender.py`.
The recommendation priority logic in `health_check_runner.py` is separate and not tier-aware.
Any change to the tier model requires touching 2–3 files.

**Solution:**
- Create `config/scoring_tiers.md` — a human-readable Markdown table that documents the
  tier model (section → tier, penalty by tier/severity, tier label, tier consequence).
- The code continues to own the Python dicts (`SECTION_TIER`, `_TIER_PENALTY`, etc.) since
  runtime parsing of Markdown is fragile; the `.md` file is the authoritative *documentation*
  that developers and stakeholders can read and edit, with code kept in sync.
- `config/scoring_tiers.md` serves as the canonical reference for BL-089 and BL-090.

**Acceptance criteria:**
- `config/scoring_tiers.md` exists with section→tier table, tier→penalty table, tier labels
- Table matches `SECTION_TIER` and `_TIER_PENALTY` exactly (verified by inspection)

---

### BL-089 · Ticket priority driven by section consequence tier
**Priority:** P1 | **Size:** S | **Epic:** 3

**Problem:** Recommendation `priority` (high/medium/low) in `_build_recommendations()` is set
ad hoc per rule — e.g. a missing-index recommendation is labeled `high` even though Missing
Indexes is a P3 section (degrades performance but never causes data loss or outage). This means
a "High priority" createIndex action competes visually with a genuinely critical oplog shrinkage
warning.

**Solution:**
- Map recommendation priority from the section's consequence tier using `SECTION_TIER`:
  - P0 sections (Server Health, Replication Health) → critical severity → `"high"`
  - P1 sections (Storage, Operations) → critical `"high"`, warning `"medium"`
  - P2 sections (Connections, Infrastructure) → critical `"medium"`, warning `"medium"`
  - P3 sections (Query Performance, Missing Indexes) → `"medium"` for critical, `"low"` for warning
  - P4 sections (Cluster Overview, Unused Indexes) → `"low"`
- Apply this mapping in `_build_recommendations()` rather than hard-coding per rule.
- Result: a missing-index action becomes `medium` or `low`; an oplog-window action becomes `high`.

**Acceptance criteria:**
- `db.orders.createIndex(...)` recommendation shows `medium` or `low` priority, not `high`
- Oplog window / replication breach recommendations show `high`
- Priority column in HTML report reflects tier-derived priority

---

### BL-090 · AI summary, score, and ticket priority alignment
**Priority:** P1 | **Size:** S | **Epic:** 3

**Problem:** Score, ticket priorities, and the LLM health summary are computed independently.
A cluster can show score=70 (P1 breach), `high` priority on a P3 index issue, and an AI
summary that doesn't mention the P1 breach — creating three inconsistent signals to the reader.

**Solution:**
- After BL-089 lands (tier-driven priorities), verify that AI summary leads with the same
  highest-tier breached section that drives the biggest score penalty.
- In `generate_health_summary()`, explicitly label which issues drove the score down:
  "Score dropped from 100 to 45 due to: Replication Health CRITICAL (P0, −50 pts)".
- Add a smoke-test assertion: if `overall_severity == CRITICAL` then the summary must
  mention at least one P0 or P1 section breach, or fall back to a template string.

**Acceptance criteria:**
- AI summary mentions the same tier(s) that caused the largest score drop
- No cluster shows `high`-priority P3 recommendations while the summary ignores a P0/P1 issue
- Summary clearly states score and the top penalty contributor

---

### BL-091 · Fleet summary tab for multi-cluster reports
**Priority:** P1 | **Size:** M | **Epic:** 7

**Problem:** The fleet HTML report opens on the first cluster's detail view. With 3+ clusters,
there is no at-a-glance overview showing all clusters side-by-side — the reader must tab
through each one manually to understand the fleet's overall health.

**Solution:**
- Add a "Summary" tab as the first (default) tab in the fleet report.
- Summary tab content:
  - Fleet-wide headline: N clusters, M critical, K warnings, overall fleet score (average or min).
  - One row per cluster: cluster name, score badge, overall severity dot, top issue (highest-tier
    breached section), recommendation count, quick-link to that cluster's tab.
  - Rows sorted by score ascending (worst first).
- No new dependencies — pure HTML/CSS table, same styling as existing report.
- Clicking a cluster row (or the "View →" link) switches to that cluster's tab via `switchCluster(idx)`.

**Acceptance criteria:**
- Summary tab is the default view when the fleet report opens
- All clusters listed with score, severity, top issue
- Clicking a cluster navigates to its detail tab
- Single-cluster runs are unaffected (no summary tab shown)

---

### BL-092 · Scoring system audit & simplification
**Priority:** P1 | **Size:** M | **Epic:** 3

**Problem:** The scoring system has grown organically across BL-021, BL-080, BL-088–091 and
now has three separate label namespaces that confuse each other:

1. **Consequence tier** (P0–P4): section groupings that drive the score penalty (e.g. Replication = P0, Missing Indexes = P3).
2. **Recommendation priority** (currently "High"/"Medium"/"Low" after the BL-089 rename): the urgency label shown in the Action Plan.
3. **Backlog priority** (P0–P3 in this BACKLOG.md): story priority for development planning.

The rename from "P0/P1/P2" to "High/Medium/Low" (applied in the previous session) removed the
collision between (1) and (2), but the user's intent is: *if a finding causes an availability
outage it should show P0 in the Action Plan*. That means recommendation priority labels should
align with consequence tiers — i.e., reuse P0–P4 semantics, not an independent 3-level scale.

**Questions to resolve:**
- Should recommendation priority use P0–P4 (matching consequence tiers) or a separate scale?
- Is the penalty table (P0 crit=−50, P1 crit=−40, …) still the right model?
- Is one penalty-per-tier (worst section wins) simpler and clearer than per-section penalties?
- Does the score formula communicate clearly to a non-expert user?
- Are there any label mismatches left after BL-089 changes?

**Deliverables:**
- Revised `config/scoring_tiers.md` with the agreed canonical model
- Unified recommendation priority label: derived from section consequence tier, shown consistently in HTML Action Plan, AI summary, and Markdown report
- Update `_REC_LBL` in `html_reporter.py` and `_rec_priority()` in `health_check_runner.py` to match agreed convention
- Verify AI summary references the same priority language as the Action Plan

**Acceptance criteria:**
- A finding in a P0-tier section (Replication/Server Health) shows "P0" in the Action Plan
- A finding in a P3-tier section (Missing Indexes/Query Performance) shows "P3" in the Action Plan
- Score breakdown, Action Plan labels, and AI summary all use the same tier vocabulary
- `config/scoring_tiers.md` is the single source of truth — no magic numbers elsewhere
- Existing health check test still produces a valid report

---

### BL-087 · OM version and agent version in report header
**Priority:** P2 | **Size:** S | **Epic:** 7

**Problem:** The report header shows cluster URI and run timestamp but not:
- MongoDB Ops Manager version (relevant for customers running OM on-prem — version
  determines which metrics API endpoints are available and whether the OM itself needs
  upgrading)
- Agent version (useful for support: "which version of the DBA agent generated this?")

**Solution:**
- Add `agent_version` to `HealthCheckReport` (populated from a `__version__` constant
  in `main_agentic.py` or a `VERSION` file).
- When OM is configured, call the OM `/api/public/v1.0/` root endpoint which returns
  `{"version": "...", ...}` — store as `om_version` on the report.
- Render both in the HTML report header row alongside cluster name and timestamp.

---

### BL-093 · Slow query threshold: count → % of total queries
**Priority:** P1 | **Size:** M | **Epic:** 3

**Problem:** `slow_query_count_warning: 5` and `slow_query_count_critical: 20` are absolute
counts. This produces false positives on busy clusters (20 slow queries out of 10M is fine)
and false negatives on quiet clusters (5 slow queries out of 10 is a 50% slow rate — serious).
A percentage threshold scales with cluster load and gives consistent signal across fleet.

**Design notes:**
- Rename thresholds: `slow_query_pct_warning: 5.0`, `slow_query_pct_critical: 20.0` (% of reads)
- Total query denominator: `opcounters.query` from serverStatus — already collected in §8 Operations
- Time-window alignment challenge: `system.profile` count reflects the current profiler session
  (may have been reset or enabled recently), while `opcounters.query` is cumulative since restart.
  Both windows must be documented in the signal tooltip so the user understands what the ratio means.
- Keep `slow_query_ms_warning` / `slow_query_ms_critical` (per-query latency thresholds) unchanged.
- Keep the raw `slow_query_count` as an informational signal (no severity). The severity signal
  becomes `slow_query_pct` with the percentage threshold.
- If `opcounters.query == 0` (no reads since restart), omit the percentage signal.

**Acceptance criteria:**
- `slow_query_count` rendered as info-only (no threshold line)
- `slow_query_pct` signal shows percentage and fires warning/critical per config
- `config/agent_config.yaml` has `slow_query_pct_warning` / `slow_query_pct_critical`
- `config/scoring_tiers.md` §3 updated to describe the new threshold semantics
- Health check still runs correctly when profiler is disabled (no slow queries → 0%)

---

### BL-086 · Metric tooltip context for non-breached signals
**Priority:** P2 | **Size:** S | **Epic:** 7

**Problem:** BL-084 enriches tooltips for *breached* signals via LLM. Non-breached
signals with no threshold (e.g. `page_faults`, throughput counters) only get a static
definition — but the reader still can't tell if their specific value is good or bad.
Example: "Page Faults: 1,817" with static tooltip "Cumulative count since last
mongod restart..." doesn't answer "is 1,817 alarming?"

**Solution:** Extend `enrich_signal_tooltips()` to also enrich a small set of
threshold-less signals that always benefit from context:
- `page_faults`: LLM compares to baseline if available; flags if high relative to uptime
- `memory_resident_mb`: LLM comments if the value seems low relative to available RAM
  (requires adding total system RAM as a signal or note)
Include these signals in the LLM batch call regardless of breach status.

---

### BL-085 · Query Performance findings — structured readable layout
**Priority:** P1 | **Size:** S | **Epic:** 7

**Problem:** The Query Performance findings block is a dense text dump that is hard
to scan. Example current output:
```
7 slow op(s) (baseline: 4.4) · threshold: 5ms · max: 19ms · avg: 9ms
3 of 7 op(s) used COLLSCAN (no index) · 0 required in-memory sort stage
  inventory [4 op(s) max 6ms avg 6ms]
    plan: unknown · docs examined: 0 · keys examined: 0 · targeting ratio: 0×
  order_items [2 op(s) max 19ms avg 18ms]
    plan: COLLSCAN · docs examined: 150,000 · targeting ratio: ∞
```
Issues:
- The summary line packs too much into one sentence — hard to scan
- Per-collection detail is shown inline as indented text — not visually distinct
- "plan: unknown · docs examined: 0" for inventory is confusing noise
- The raw collection breakdown belongs in a collapsible Details panel (BL-083)

**Solution:**
- Summary line: keep key signals only — slow count vs baseline, COLLSCAN count, worst
  collection. Everything else into Details.
- Per-collection block: render as a small structured table or card in the Details panel
  (once BL-083 is implemented), not inline text.
- Suppress collections where `docs_examined == 0` and plan is unknown — these are
  likely internal operations or profiler noise, not real slow queries.
- Depends on: BL-083 (collapsible Details).

---

### BL-084 · Metric card tooltips with LLM-contextual explanation
**Priority:** P1 | **Size:** M | **Epic:** 7

**Problem:** Metric cards show a number and a unit — but readers who are not MongoDB
experts cannot interpret them without external knowledge. For example:

- "Cluster Targeting Ratio: 1,345.5 docs scanned per read" — what's bad about that?
- "WT Cache Hit Ratio: 100.0%" — is that good or bad?
- "Page Faults: 1,723 (cumulative)" — is 1,723 alarming?
- "Lock Wait Pct: 0.0%" — what would a non-zero value mean?

A customer reviewing the report with their manager, or a DBA new to MongoDB, needs
context to act on these numbers. The industry standard pattern is an **ⓘ info icon**
next to the metric label that reveals an explanation on hover (desktop) or tap (mobile).

**Two-tier implementation:**

**Tier 1 — Static tooltips (always available, no LLM required):**
Add a `_METRIC_TOOLTIPS` dict in `html_reporter.py` mapping signal names to a short
(1–2 sentence) definition of what the metric means and what the threshold represents.
Rendered as a CSS-only tooltip — no JavaScript, works in offline/air-gapped reports.
Example entries:
```
"cluster_targeting_ratio": "Docs examined ÷ docs returned across all queries. A ratio
  above 10 means queries are scanning far more data than needed — usually a missing index.",
"wt_cache_hit_ratio": "Percentage of reads served from WiredTiger's in-memory cache.
  Below 95% means MongoDB is reading from disk, which significantly slows queries.",
"page_faults": "Cumulative count since last mongod restart of data pages read from disk
  because they were not in memory. The rate between runs matters more than the total.",
"lock_wait_pct": "Percentage of time operations waited to acquire a global lock.
  Above 5% indicates write contention or long-running operations blocking others.",
"memory_resident_mb": "RAM currently used by the mongod process. In production this
  should be close to total server RAM — MongoDB caches as much of the working set as possible.",
```

**Tier 2 — LLM-contextual interpretation (optional, enriches at report generation time):**
When LLM enrichment is enabled (`llm_recommendations: true`), generate a one-sentence
*contextual* interpretation for each breached or noteworthy signal — e.g.:
> "Your targeting ratio of 1,345 is 134× above threshold — consistent with the full
> collection scans on `ecommerce.order_items` identified in §6."

Store these interpretations as a `tooltip` field on the `Signal` model. The HTML renderer
shows the static tooltip for healthy signals and the LLM interpretation for breached ones.
LLM generation is fire-and-forget per signal; failure falls back to static tooltip silently.

**UI specification:**
- Label row: `[metric name]  ⓘ`
- The ⓘ is a `<span class="metric-info">` with `aria-label` and CSS `:hover` tooltip.
- Tooltip box: max-width 280px, positioned above the card, dark surface background,
  13px font, z-index above neighbouring cards.
- On mobile (touch): tooltip visible on tap, dismissed on tap-outside.
  Use a CSS `:focus-within` trick on a visually-hidden `<button>` — no JS required.

**Data model change (`Signal`):**
```python
class Signal(BaseModel):
    name: str
    value: Any
    unit: str | None = None
    threshold: Any | None = None
    tooltip: str | None = None   # static or LLM-generated explanation
```

**Acceptance criteria:**
- Every signal in `_METRIC_TOOLTIPS` shows an ⓘ icon next to its label.
- Hovering/tapping the ⓘ shows the tooltip without JavaScript.
- Breached signals show LLM interpretation when available; static tooltip as fallback.
- `Signal.tooltip` field is optional — existing code not broken by addition.
- HTML output remains self-contained (no external CSS/JS dependencies).
- End-to-end health check passes; tooltip content verified for all §8 Operations signals.

---

### BL-083 · HTML report — collapsible "Details" panel per section
**Priority:** P1 | **Size:** S | **Epic:** 7

**Problem:** Every section always shows its full findings list, even when the section is
healthy and the findings carry no actionable signal. A reader scanning a 10-section
report must scroll past walls of green-section bullets to reach the real issues.

**Solution:** Wrap the findings list in a native HTML `<details><summary>Details
</summary>…</details>` element — no JavaScript required.

- Sections with severity WARNING or CRITICAL: `<details open>` (expanded by default —
  the reader must see the issue).
- Sections with severity OK: `<details>` (collapsed by default — reader can expand if
  curious, but the clean scan path stays noise-free).
- Summary label: use industry-standard wording — **"Show details"** / **"Hide details"**
  (matches the pattern used by GitHub, Datadog, PagerDuty incident timelines).

**Acceptance criteria:**
- OK sections render collapsed; WARNING/CRITICAL sections render expanded.
- Findings content is identical to current — only the visibility default changes.
- No JavaScript added; native `<details>` toggle works in all modern browsers.
- End-to-end health check passes; HTML output verified visually.

---

### BL-082 · HTML report — sidebar & content restructure
**Priority:** P1 | **Size:** S | **Epic:** 7

**Problem:** The current sidebar grouping was assembled incrementally and does not
reflect how an experienced DBA thinks about a cluster health report. Specific issues
identified in critical review:

1. **"Alerts" misplaced under Overview.** Active alerts is a cross-cutting summary —
   the first thing a reader wants to see. In standard DBA reports (MongoDB PS health
   check templates, OpsManager dashboards, Datadog MongoDB integration), the alert
   summary is always the top-of-report executive summary, not a sub-item under Overview.

2. **"Index analysis" in Performance is wrong — and broken.** Index gaps and unused
   indexes are *configuration findings / action items*, not performance metrics.
   Performance = throughput, latency, scan ratios, cache efficiency. Index analysis
   belongs in its own advisory group. Additionally, the current nav item "Index analysis"
   jumps to `#sec-indexes` (Missing Indexes only) — Unused Indexes has **no nav link**
   and is unreachable from the sidebar.

3. **"Operations" under Performance is misleading.** serverStatus signals (resident
   memory, page faults, lock wait %, WT cache hit ratio) are *resource health* metrics,
   not query-performance metrics. A DBA expects these under "Cluster Health" or
   "Resource Utilization". Mixing them with slow queries under one "Performance" group
   creates a confusing category boundary.

4. **"Storage" under Reliability is incorrect.** Storage capacity exhaustion is a
   *capacity* concern, not a reliability concern. Reliability = HA, replication,
   failover. Capacity = disk usage, memory pressure, connection limits.
   A DBA looking for replication lag should not have to scan past storage metrics.

5. **Content scroll order does not match nav group order.** Nav says Overview →
   Performance → Reliability → Action, but content renders: Cluster, Server, Alerts,
   Queries, Missing Indexes, Unused Indexes, Operations, Connections, Infrastructure,
   Replication, Storage. A reader clicking a nav item and then scrolling gets confused
   because adjacent sections belong to different nav groups.

6. **"Server Health" hidden inside Overview nav group.** Server health (version, uptime,
   disk) is infrastructure detail — it belongs in a Cluster Health group alongside
   replication state, not paired with the summary overview.

**Proposed structure** (based on standard MongoDB DBA health check practice):

```
Sidebar nav groups (top → bottom):
┌─ Summary ──────────────────────────────────────────┐
│  Cluster Overview                                  │
│  Active Alerts                                     │
├─ Availability ─────────────────────────────────────┤
│  Replication Health                                │
│  Connections & Concurrency                         │
├─ Resource Health ───────────────────────────────────┤
│  Server Health           (version, uptime, disk)  │
│  Storage & Capacity                                │
│  Infrastructure          (CPU, IOPS, memory — OM) │
├─ Performance ───────────────────────────────────────┤
│  Query Performance       (slow queries, scans)    │
│  Operations              (cache, locks, memory)   │
├─ Index Advisory ────────────────────────────────────┤
│  Missing Indexes                                   │
│  Unused Indexes                                    │
└─ Action Plan ───────────────────────────────────────┘
   Recommendations
```

Content scroll order must match nav group top-to-bottom order.

**Rationale (DBA mental model):**
- *"Is the cluster up and healthy right now?"* → Summary + Availability
- *"Are we about to run out of resources?"* → Resource Health
- *"Is it performing well?"* → Performance
- *"What should we tune?"* → Index Advisory
- *"What do I do next?"* → Action Plan

**Acceptance criteria:**
- Sidebar nav groups and content scroll order match the proposed structure exactly.
- All 10 sections + Alerts + Recommendations have a visible nav link.
- Unused Indexes has its own nav link (currently missing).
- Active scroll-highlight (IntersectionObserver) continues to work correctly.
- End-to-end health check passes; HTML output verified visually.

---

### BL-081 · HTML report — zero-duplication layout
**Priority:** P1 | **Size:** S | **Epic:** 7

**Problem:** Every section card renders the same data twice — once in metric cards and
again as plain-text findings bullets. Examples:

- §1 Cluster Overview: "Database Count: 1 / Collection Count: 5" in metric cards, then
  "1 user database(s), 5 collection(s) total." + full collection name list as findings —
  the count is already in the cards; the name list is noise unless a collection has a
  problem.
- §2 Server Health: version, uptime, disk GB, disk % in metric cards, then
  "MongoDB 8.0.20 · host: rs-node-1 · uptime: 1.4h" + "Filesystem disk: 3.8 GB used of
  19.2 GB (19.9%)" as findings — identical data, different format.
- §9/§10 partially fixed in 0.7.1; the same pattern must be applied to all sections.

Also, metric card labels are auto-generated from snake_case producing ugly strings:
"Mongodb Version", "Filesystem Disk Used Gb", "Database Count" — §9/§10 fixed in
0.7.1 via `_SIGNAL_LABELS`; §1 and §2 still need the same treatment.

**Solution:**

1. **Findings = alerts + non-redundant context only.** Remove any finding line whose
   value is already shown in a metric card. Keep: threshold-breach warnings, host name
   in §2 (not in any card), macOS/APFS disk note, partition name in §10. Rule: if the
   reader can read the same number from a card, the finding line adds nothing.

2. **Collection list — show only on problem.** In §1, omit the unconditional collection
   name list. Add it back only when ≥1 collection has a finding in §5–§7, and phrase it
   as a cross-reference: "ecommerce.orders — see Missing Indexes."

3. **Extend `_SIGNAL_LABELS` to §1 and §2:**
   - `database_count` → "Databases", `collection_count` → "Collections"
   - `mongodb_version` → "Version", `uptime_hours` → "Uptime"
   - `filesystem_disk_used_gb` → "Disk Used", `filesystem_disk_used_pct` → "Disk Used %"

**Acceptance criteria:**
- No finding line repeats a value already visible in a metric card for the same section.
- §1 collection list only appears when ≥1 collection has a finding in §5–§7.
- Metric card labels for §1 and §2 are human-friendly (no "Mongodb", no raw "Gb").
- All 10 sections audited — no new duplication introduced.
- End-to-end health check passes; HTML and JSON reports written without error.

---

### BL-060 · HTML report output
**Priority:** P1 | **Size:** M | **Epic:** 7

`src/utils/html_reporter.py` — pure Python, zero new dependencies. Dark-theme
self-contained HTML with overall severity banner, per-section cards (signals table +
findings), and recommendations table. Written alongside the JSON file in `reports/`.
Output: ~10 KB per report (well under 100 KB target).

---

### BL-020 · Structured health check report format
**Priority:** P0 | **Size:** S | **Epic:** 3

Typed dataclass schema (`HealthCheckReport`, `ReportSection`, `Signal`, `Recommendation`, `HealthSeverity`)
saved as versioned JSON to `reports/`. Rich console renderer in `main_agentic.py`.

---

### BL-001 · Server & connection health tool
**Priority:** P0 | **Size:** M | **Epic:** 1

Server Health section in `HealthCheckRunner`: version, hostname, uptime via `local.startup_log`;
disk usage (fsUsedSize/fsTotalSize) via `db-stats` on admin DB. Note: connections/memory/page faults
not obtainable via MCP (no `serverStatus` equivalent).

---

### BL-002 · Replication health tool
**Priority:** P0 | **Size:** M | **Epic:** 1

Replication Health section: RS config and member list via `local.system.replset`; oplog window
(head/tail timestamps) via `local.oplog.rs`. Standalone instances handled gracefully ("not configured", OK severity).
Note: per-member lag not available without `replSetGetStatus`.

---

### BL-003 · Collection storage stats tool
**Priority:** P0 | **Size:** M | **Epic:** 1

Storage & Capacity section: per-DB sizes via `db-stats`; per-collection sizes via `collection-storage-size`;
document counts via `count`. Computes avg bytes/doc and flags collections over threshold.

---

### BL-004 · Index usage statistics tool
**Priority:** P0 | **Size:** M | **Epic:** 1

Index Usage section: `aggregate $indexStats` pipeline per collection. Parses BSON int64 `accesses.ops`
(`{low, high, unsigned}` representation). Identifies unused indexes (ops=0), excludes `_id_` from
drop candidates.
