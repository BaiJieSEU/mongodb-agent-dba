# MongoDB DBA Agent — Product Backlog

Updated: 2026-03-29 | Format: Epic → Story → Acceptance criteria

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
| BL-083 | HTML report — collapsible Details panel per section | P1 | S | 7 | ✅ Done |
| BL-084 | Metric card tooltips with LLM-contextual explanation | P1 | M | 7 | ✅ Done |
| BL-085 | Query Performance findings — structured readable layout | P1 | S | 7 | ✅ Done |
| BL-088 | Score & ticket tiering table in Markdown config | P1 | S | 3 | ✅ Done |
| BL-089 | Ticket priority driven by section consequence tier | P1 | S | 3 | ✅ Done |
| BL-090 | AI summary, score, and ticket priority alignment | P1 | S | 3 | ✅ Done |
| BL-091 | Fleet summary tab for multi-cluster reports | P1 | M | 7 | ✅ Done |
| BL-092 | Scoring system audit & simplification | P1 | M | 3 | ✅ Done |
| BL-093 | Slow query threshold: count → % of total queries | P1 | M | 3 | ✅ Done |
| BL-086 | Metric tooltip context for non-breached signals (page faults, throughput) | P2 | S | 7 | 🔲 |
| BL-087 | OM version and agent version in report header | P2 | S | 7 | ✅ Done |
| BL-061 | Markdown report output | P2 | S | 7 | ✅ Done |
| BL-075 | Data sovereignty mode | P2 | S | 8 | 🔲 |
| BL-080 | Health rating formula — transparency in report | P2 | S | 7 | ✅ Done |
| BL-072 | Non-Docker quickstart script | P2 | M | 8 | 🔲 |
| BL-040 | Approval-gated index creation | P2 | L | 5 | 🔲 |
| BL-051 | REST API + Web UI | P2 | XL | 6 | 🔲 |
| BL-094 | Replication lag threshold + member up/down signals | P1 | S | 1 | ✅ Done |
| BL-095 | Index size per collection in Storage & Capacity | P1 | S | 1 | ✅ Done |
| BL-096 | Exact duplicate index detection | P1 | S | 1 | ✅ Done |
| BL-097 | Active long-running operations signal | P1 | S | 1 | ✅ Done |
| BL-100 | Profiler slowms as explicit report signal | P1 | S | 1 | ✅ Done |
| BL-102 | Aggregation pipeline anti-patterns in Query Performance | P1 | M | 1 | ✅ Done |
| BL-106 | Backup configuration detection | P1 | M | 9 | ✅ Done |
| BL-107 | Restore readiness check | P1 | M | 9 | ✅ Done |
| BL-098 | Page fault rate / trend signal | P2 | S | 1 | ✅ Done |
| BL-099 | Network throughput signals (bytesIn/Out) | P2 | S | 1 | ✅ Done |
| BL-101 | Index cardinality / quality check | P2 | M | 1 | ✅ Done |
| BL-103 | Query plan cache hit rate | P2 | M | 1 | ✅ Done |
| BL-124 | WiredTiger engine pressure — tickets & dirty ratio | P1 | S | 1 | 🔲 |
| BL-125 | Plan cache stats audit on low hit rate | P1 | M | 1 | 🔲 |
| BL-104 | Batch vs 24×7 workload detection | P2 | M | 1 | 🔲 |
| BL-105 | Collection-level read/write ratio | P2 | M | 1 | 🔲 |
| BL-109 | Monitoring alert coverage quality | P2 | M | 9 | 🔲 |
| BL-108 | Hot shards + chunk distribution (conditional) | P2 | L | 9 | 🔲 |
| BL-123 | OM-based cluster auto-discovery — bootstrap cluster list from OM API | P1 | M | 9 | 🔲 |
| BL-042 | Drop unused index (approval-gated) | P3 | S | 5 | 🔲 |
| BL-053 | MongoDB Atlas integration | P3 | L | 6 | 🔲 |
| BL-110 | Copy-to-clipboard for Action Plan commands | P1 | S | 10 | ✅ Done |
| BL-111 | Active Alerts — jump-to-section links | P1 | S | 10 | ✅ Done |
| BL-112 | Fleet summary — aggregate fleet score + critical cluster banner | P1 | S | 10 | ✅ Done |
| BL-113 | Score ring at top of sidebar (above nav) | P1 | S | 10 | ✅ Done |
| BL-114 | Trend arrows on metric cards (vs prior baseline run) | P1 | M | 10 | ✅ Done |
| BL-115 | Replication lag human-readable duration (Xh Ym) | P1 | S | 10 | ✅ Done |
| BL-116 | Action Plan — group recommendations by priority tier | P1 | S | 10 | ✅ Done |
| BL-117 | Fix `<details>` accessibility — inline summary text, not CSS `::before` | P1 | S | 10 | ✅ Done |
| BL-118 | Light mode / auto theme (prefers-color-scheme) | P2 | M | 10 | ✅ Done |
| BL-119 | Print-friendly CSS for single-cluster report | P2 | S | 10 | ✅ Done |
| BL-120 | Metric headroom indicator — safe distance to threshold on OK cards | P2 | S | 10 | 🔲 |
| BL-121 | Placeholder sections — collapse or visually de-emphasise when OM not configured | P2 | S | 10 | ✅ Done |
| BL-122 | Historical score sparkline per cluster in Fleet Summary | P2 | M | 10 | ✅ Done |

**Done:** 64 items (BL-020 through BL-123, see full list in git log)
**Partial:** 1 item (BL-071 — LLM+MongoDB env vars done, full coverage pending)
**P0:** 1 remaining — scheduler (BL-011)
**P1:** 17 items remaining
**P2–P3:** 11 items remaining
**Total:** 86 items across 10 epics (57 done, 1 partial, 28 remaining)

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

## Epic 9 — PS Health Check Coverage Gaps

*Goal: close the gaps identified in the PS health check review (2026-03-27).
Items 13 map to existing report sections; 4 require new sections (§9 Backup & Recovery,
§10 Sharding, §11 Alerting Coverage). No new sections should be created until at least
BL-106/107 are implemented so Backup & Recovery has meaningful content.*

---

### BL-094 · Replication lag threshold + member up/down signals
**Priority:** P1 | **Size:** S | **Epic:** 9 | **Section:** §3 Replication Health

**Story:** As a DBA, I want §3 Replication Health to report explicit per-member
replication lag and node up/down status so I can detect a lagging or missing secondary
before it puts the cluster at risk.

**Context:** The current implementation reads `local.system.replset` for RS config and
`local.oplog.rs` for oplog window. `replSetGetStatus` is not available via MCP. However,
`local.system.replset` contains `lastHeartbeatRecv` and `optimeDate` per member from the
**primary's** perspective — available without `replSetGetStatus`.

**Metrics to add (all from `local.system.replset` — existing MCP source):**

| Signal | Source field | Threshold |
|--------|-------------|-----------|
| `replication_lag_max_sec` | `max(now - member.optimeDate)` across non-primary members | WARN >10s, CRIT >60s |
| `members_up` | count of members where `health == 1` | CRIT if < majority |
| `members_down` | count of members where `health == 0` | WARN ≥1, CRIT ≥ majority |

**Acceptance criteria:**
- `_section_replication_health()` extracts `optimeDate` and `health` per member from
  `local.system.replset` result already fetched by the section
- New signals: `replication_lag_max_sec`, `members_up`, `members_down`
- Finding text names the lagging/down member (e.g. `"secondary rs-node-2:27017 is 45 s behind"`)
- Severity WARNING if any member has lag > 10 s or health == 0; CRITICAL if lag > 60 s or
  a majority of members are unhealthy
- Standalone gracefully remains "not applicable"

---

### BL-095 · Index size per collection in Storage & Capacity
**Priority:** P1 | **Size:** S | **Epic:** 9 | **Section:** §4 Storage & Capacity

**Story:** As a DBA, I want §4 Storage & Capacity to show index size alongside data size
for each collection so I can detect index bloat and plan capacity correctly.

**Data source:** `db-stats` already returns `indexSize` at the database level (already
fetched). `collection-stats` (via `collection-storage-size` MCP tool) returns per-collection
data size. The MCP `db-stats` tool response includes `indexSize` — already available.

**Metrics to add:**

| Signal | Source | Threshold |
|--------|--------|-----------|
| `total_index_size_mb` | `db-stats.indexSize / 1024²` summed across DBs | INFO only |
| `index_to_data_ratio` | total index size / total data size | WARN if > 2× |

**Acceptance criteria:**
- `_section_storage_capacity()` extracts `indexSize` from existing `db_stats()` result
- New signals: `total_index_size_mb`, `index_to_data_ratio`
- Finding text: `"Index size (X MB) is Y× data size — consider reviewing unused indexes"`
  when ratio > 2
- Severity WARNING if `index_to_data_ratio > 2`; OK otherwise

---

### BL-096 · Exact duplicate index detection
**Priority:** P1 | **Size:** S | **Epic:** 9 | **Section:** §7 Unused Indexes

**Story:** As a DBA, I want the health check to detect indexes with identical key
patterns on the same collection so I can safely drop exact duplicates that waste RAM
and slow writes.

**Context:** BL-007 delivered left-prefix redundancy detection (e.g. `{a:1}` redundant
when `{a:1, b:1}` exists). This BL adds exact duplicate detection (two indexes with
identical key specs, regardless of options like sparse/partial).

**Data source:** `collection-indexes` MCP tool — already called per collection in §6.

**Logic:** For each collection, group indexes by their canonical key spec (sorted key
names + direction). Any group with ≥2 members contains duplicates — flag all but the
one with the lower index size.

**Acceptance criteria:**
- Exact duplicate pairs reported as a CRITICAL finding (exact duplicates are always safe
  to drop — no query plan benefits from a true duplicate)
- Recommendation: `dropIndex(<duplicate_name>)` with evidence `"identical key pattern as <kept_index>"`
- Distinguishes exact duplicates from left-prefix redundancies (BL-007)
- Result adds to existing §7 Unused Indexes section — no new section needed

---

### BL-097 · Active long-running operations signal
**Priority:** P1 | **Size:** S | **Epic:** 9 | **Section:** §8 Operations

**Story:** As a DBA, I want §8 Operations to surface currently running operations that
have been active for longer than a threshold so I can identify blocking queries before
they cascade.

**Context:** BL-005 proposes a full `currentOp` tool via MCP (MCP blocker still open).
This BL uses `serverStatus.currentOp` (available via existing direct PyMongo path) as a
lighter alternative that counts active operations by duration bucket.

**Data source:** `serverStatus` — already fetched in `_section_operations()`.

**serverStatus path:** `serverStatus.currentOp` is not present. Use
`serverStatus.globalLock.currentQueue` for queued operations count and
`serverStatus.metrics.operation.writeConflicts` for conflicts. Alternatively, expose
`db.adminCommand({currentOp: 1, active: true, secs_running: {$gte: 5}})` via the
existing direct PyMongo path in `MongoDBManager`.

**Implementation choice:** Extend `MongoDBManager.get_server_status()` (or add a
companion `get_current_op()`) that calls `currentOp` with `{active: true, secs_running: {$gte: 5}}`.

**Acceptance criteria:**
- New signal `long_running_ops_count` = count of active operations running ≥ 5 s
- Optional signal `longest_op_sec` = duration of the single slowest active operation
- Severity WARNING if `long_running_ops_count > 0`; CRITICAL if `longest_op_sec > 60`
- Finding text lists the top 3 long-running ops by duration and namespace
- Gracefully skips if `currentOp` is not accessible (insufficient privileges)
- Note: resolves the signal gap identified by BL-005; BL-005 remains for full MCP tool integration

---

### BL-098 · Page fault rate / trend signal
**Priority:** P2 | **Size:** S | **Epic:** 9 | **Section:** §8 Operations

**Story:** As a DBA, I want the Operations section to track the page fault rate trend
between runs rather than reporting the raw cumulative count (which is always increasing)
so I can tell whether memory pressure is growing or stable.

**Context:** `serverStatus.extra_info.page_faults` is a cumulative counter since mongod
start — already collected. A single value is not actionable. A delta between consecutive
runs is.

**Implementation:** Use `BaselineManager` rolling window to compute delta:
`current_page_faults - previous_page_faults_mean`. If the instance was restarted between
runs the delta is invalid — detect by checking `serverStatus.uptimeMillis < run_interval`.

**Acceptance criteria:**
- Signal `page_fault_delta` = difference from rolling baseline (not absolute count)
- During cold-start: report raw count with note "(baseline not yet established)"
- Severity WARNING if delta > 2× baseline delta; CRITICAL if delta > 5× baseline delta
- Hard limit: if raw page_faults > 1000/s (computed from uptime), always CRITICAL
- Finding text: `"Page faults increased by X vs. baseline of Y/run — possible memory pressure"`

---

### BL-099 · Network throughput signals (bytesIn/Out)
**Priority:** P2 | **Size:** S | **Epic:** 9 | **Section:** §8 Operations

**Story:** As a DBA, I want §8 Operations to show network throughput (bytes in and out)
so I can detect replication bandwidth saturation or unexpected traffic spikes.

**Data source:** `serverStatus.network.bytesIn`, `serverStatus.network.bytesOut` —
cumulative counters; already available via the existing `get_server_status()` path.

**Acceptance criteria:**
- New signals: `network_bytes_in_mb`, `network_bytes_out_mb` (cumulative since restart)
- Signal `network_bytes_out_to_in_ratio` — unusually high ratio (> 10×) may indicate
  large result sets returned to clients
- Severity: INFO only (no static threshold — baseline comparison via BL-021 handles trends)
- Displayed in the Operations signals table; no WARNING/CRITICAL from static thresholds

---

### BL-100 · Profiler slowms as explicit report signal
**Priority:** P1 | **Size:** S | **Epic:** 9 | **Section:** §5 Query Performance

**Story:** As a DBA reviewing a health report, I want to see the profiler's `slowms`
threshold alongside slow query findings so I can judge whether the query sample is
representative (a 200 ms threshold misses many problems a 5 ms threshold would catch).

**Data source:** `system.profile` documents include `op: "command"` entries for
`profile` admin commands, but the cleaner source is `db.getProfilingStatus()` — already
queried by BL-006.

**Implementation:** The profiler status is already available after §5 runs. Expose
`slowms` as an explicit `Signal` in the §5 report section.

**Acceptance criteria:**
- New signal `profiler_slowms` added to §5 Query Performance signals list
- Severity WARNING if `slowms > 100` (too coarse — important queries may be missed)
- Severity OK if `slowms ≤ 50`
- Finding text if WARNING: `"Profiler threshold is Xms — slow queries faster than Xms are not captured"`
- Profiler-off state (level 0) already handled by BL-006; this BL assumes profiler is on

---

### BL-101 · Index cardinality / quality check
**Priority:** P2 | **Size:** M | **Epic:** 9 | **Section:** §6 Missing Indexes

**Story:** As a DBA, I want §6 Missing Indexes to flag recommended indexes where the
candidate field has very low cardinality (e.g. a boolean `isActive` field) so I don't
create indexes that MongoDB's query planner will ignore anyway.

**Context:** When `_build_recommendations()` suggests `createIndex({field: 1})`, the field
may be a boolean or a small enumerable. MongoDB typically won't use such an index when
selectivity < ~3%. The check needs an estimate of distinct values.

**Data source:** MCP `aggregate` with `$group` on the candidate field + `$count`:
```
[{"$group": {"_id": "$<field>"}}, {"$count": "distinct"}]
```
Limited to a sample of the collection to avoid performance impact.

**Acceptance criteria:**
- For each index recommendation with a single field, run a cardinality estimate
  (capped at 10,000 docs via `$sample`)
- If distinct count / sample size < 0.03 (3%), downgrade confidence to `low` and add
  finding: `"Field '<field>' has low cardinality (N distinct values in sample) — index
  unlikely to be selected by query planner"`
- Does not suppress the recommendation — still emitted, but with `confidence: low`
- Cardinality check skipped for compound indexes (too expensive to enumerate combinations)
- Adds `cardinality_check_skipped: true` signal when collection is > 1M docs and sample
  would be too slow

---

### BL-102 · Aggregation pipeline anti-patterns in Query Performance
**Priority:** P1 | **Size:** M | **Epic:** 9 | **Section:** §5 Query Performance

**Story:** As a DBA, I want §5 Query Performance to detect slow aggregation pipelines
in the profiler and flag common anti-patterns (`$match` after `$group`, `$lookup` without
index, `$unwind` before `$match`) so I can fix the most expensive pipelines.

**Context:** BL-008 proposed full `explain` on aggregation pipelines. This BL delivers a
lighter version: pattern-match on the `command.pipeline` field in `system.profile` to
detect anti-patterns without running `explain` on every pipeline.

**Data source:** `system.profile` — already queried. Profiler records `command.pipeline`
for aggregation operations.

**Anti-patterns to detect:**

| Pattern | Detection | Impact |
|---------|-----------|--------|
| `$match` after `$group` | `$group` appears before `$match` in pipeline array | Full scan before filter |
| `$lookup` with no index on `from.localField` | Check indexes on joined collection | Full join scan |
| `$sort` without index (large collection) | `hasSortStage: true` + no index covers sort key | Memory sort / disk spill |
| `$unwind` before `$match` | `$unwind` precedes `$match` | Cartesian explosion before filter |

**Acceptance criteria:**
- `_section_query_performance()` parses `command.pipeline` from profiler entries where `op == "command"`
- Each anti-pattern detected adds a finding with the collection, the anti-pattern name, and fix advice
- Recommendation: restructured pipeline snippet showing corrected stage order
- `slow_aggregation_count` signal added to §5
- Extends BL-008 scope; BL-008 remains for full `explain` integration

---

### BL-103 · Query plan cache hit rate
**Priority:** P2 | **Size:** M | **Epic:** 9 | **Section:** §5 Query Performance

**Story:** As a DBA, I want §5 Query Performance to report the query plan cache hit rate
so I can detect workloads that are constantly re-planning (cache thrashing) which adds
CPU overhead on every request.

**Data source:** `serverStatus.metrics.queryPlanner.planCacheTotalQueryShapes` and
`serverStatus.metrics.queryPlanner.planCacheHits` / `planCacheMisses` — available via
existing `get_server_status()` path.

**Note:** These counters were added in MongoDB 7.0. Add a version check; gracefully skip
on MongoDB < 7.0 with a note.

**Acceptance criteria:**
- New signals: `plan_cache_hits`, `plan_cache_misses`, `plan_cache_hit_rate_pct`
- `plan_cache_hit_rate_pct = hits / (hits + misses) * 100`
- Severity WARNING if hit rate < 80%; CRITICAL if < 50%
- Finding text: `"Plan cache hit rate is X% — query planner is re-planning frequently"`
- Gracefully skips on MongoDB < 7.0 with finding: `"Plan cache metrics not available (requires MongoDB 7.0+)"`

---

### BL-104 · Batch job vs 24×7 workload detection
**Priority:** P2 | **Size:** M | **Epic:** 9 | **Section:** §5 Query Performance

**Story:** As a DBA, I want the health check to detect whether slow query spikes are
caused by periodic batch jobs (acceptable) vs. continuous 24×7 load (needs fixing) so
recommendations are correctly prioritised.

**Context:** A batch job that runs once a night may produce 500 slow queries at 02:00
but the cluster is healthy at all other times. Flagging this as CRITICAL (same as a
continuous high load) leads to noise.

**Data source:** `system.profile` timestamp distribution — already fetched. Analyse
`ts` field distribution across the slow query sample.

**Detection heuristic:**
- Compute `slow_query_count` per hour bucket for the last 24 h
- If max(bucket) / mean(non-zero-buckets) > 5×, classify as "bursty / batch"
- If all buckets are within 2× of mean, classify as "continuous"

**Acceptance criteria:**
- New signal `workload_pattern`: `"bursty"` | `"continuous"` | `"unknown"` (< 2 h data)
- If `bursty`: downgrade severity one level (CRITICAL → WARNING, WARNING → OK) and add
  finding: `"Slow query spike appears batch-related (Xh burst pattern) — verify this is expected"`
- If `continuous`: keep severity unchanged
- Pattern stored in baseline for trend comparison across runs

---

### BL-105 · Collection-level read/write ratio
**Priority:** P2 | **Size:** M | **Epic:** 9 | **Section:** §8 Operations

**Story:** As a DBA, I want §8 Operations to show the read/write ratio per busy
collection so I can identify write-heavy collections that need write-optimised indexes
vs. read-heavy collections that need query indexes.

**Data source:** `system.profile` — already fetched. Profile entries include `op` field
(`find`, `insert`, `update`, `delete`, `command`). Group by `(db, collection, op)` from
the existing slow query sample.

**Note:** This reflects the *slow* query read/write ratio, not the full workload ratio.
Make this clear in the finding text.

**Acceptance criteria:**
- For the top 5 collections by slow query count, compute `read_count`, `write_count`,
  `rw_ratio` from profiler data
- New signal `top_collection_rw_ratio` emitted as a structured finding (not a scalar signal)
- Finding text: `"orders: 80% reads / 20% writes (from slow query sample)"`
- Severity: INFO only — no threshold breach from this signal alone
- Useful context for index recommendations in §6

---

### BL-106 · Backup configuration detection
**Priority:** P1 | **Size:** M | **Epic:** 9 | **Section:** §9 Backup & Recovery (NEW)

**Story:** As a DBA, I want the health check to detect whether a backup solution is
configured and when the last backup completed so I can assess data recovery readiness
without manually checking backup tooling.

**New section:** §9 Backup & Recovery — consequence tier P1 (Outage: no backup means
unrecoverable failure on disk loss). This section is created when BL-106 is implemented.

**Detection approach (no backup agent access needed):**
MongoDB backup solutions leave traces readable via the MCP/serverStatus path:

| Backup tool | Detection method |
|------------|-----------------|
| MongoDB Ops Manager / Cloud Manager | `serverStatus.backupCursorOpen` — non-null if hot backup cursor is open |
| mongodump (file-based) | Cannot detect — note as "unknown, verify manually" |
| Atlas backup | Not applicable (Atlas-managed) |
| `$backupCursor` (4.2+) | Query `admin.$cmd.aggregate` with `{$backupCursorExtend}` — presence of the cursor indicates active backup |

**Signals to emit:**

| Signal | Source | Note |
|--------|--------|------|
| `backup_cursor_open` | `serverStatus.storageEngine.backupCursorOpen` (if present) | Boolean |
| `backup_method_detected` | String: `"ops_manager"` \| `"mongodump"` \| `"unknown"` | From heuristics |

**Acceptance criteria:**
- New `_section_backup_recovery()` method in `HealthCheckRunner`
- If no backup signal detected: severity WARNING + finding `"No backup solution detected — verify backup configuration manually"`
- If backup cursor open: severity OK + finding `"Hot backup cursor is open — backup appears active"`
- Section renders in HTML/Markdown/JSON report as §9 Backup & Recovery
- `SECTION_TIER["Backup & Recovery"] = "P1"` added to `html_reporter.py`

---

### BL-107 · Restore readiness check
**Priority:** P1 | **Size:** M | **Epic:** 9 | **Section:** §9 Backup & Recovery

**Story:** As a DBA, I want the health check to assess restore readiness by checking
whether the oplog window is sufficient to perform a point-in-time restore so I can
detect when the oplog is too short to bridge the backup-to-restore gap.

**Context:** For replica set point-in-time restore (PITR), the oplog window must be
longer than the backup interval. If backups run daily, the oplog must cover > 24 h.
The oplog window is already computed in §3 Replication Health.

**Acceptance criteria:**
- `_section_backup_recovery()` (created by BL-106) reads the oplog window from the §3
  result (pass as parameter or read from shared state)
- Signal `pitr_window_hours` = oplog window hours (same value as §3)
- Signal `pitr_viable` = boolean: True if oplog window > configurable backup interval
  (default: 24 h, configurable via `thresholds.backup_interval_hours`)
- Severity WARNING if `pitr_window_hours < backup_interval_hours`
- CRITICAL if `pitr_window_hours < 2` (already caught by §3 hard limit — note cross-reference)
- Finding text: `"Oplog window (Xh) is shorter than backup interval (Yh) — PITR may not be possible"`
- New config: `thresholds.backup_interval_hours: 24`

---

### BL-108 · Hot shards + chunk distribution (conditional)
**Priority:** P2 | **Size:** L | **Epic:** 9 | **Section:** §10 Sharding (NEW, conditional)

**Story:** As a DBA managing a sharded cluster, I want the health check to detect hot
shards and uneven chunk distribution so I can identify balancer issues or poor shard key
choices before they cause performance degradation.

**Conditional section:** §10 Sharding only renders if the cluster is sharded. Detection:
`serverStatus.process == "mongos"` or `serverStatus.sharding` key is present.

**New section:** §10 Sharding — consequence tier P2 (Degraded: hot shard causes slow
queries on that shard; cluster stays available).

**Data source:** Config server `config.chunks` collection — readable via MCP `find` on
the `config` database. Available from a `mongos` connection.

**Metrics:**

| Signal | Source | Threshold |
|--------|--------|-----------|
| `shard_count` | `config.shards` count | INFO |
| `chunk_count` | `config.chunks` count | INFO |
| `chunk_imbalance_ratio` | max_chunks_on_shard / min_chunks_on_shard | WARN > 1.5, CRIT > 3 |
| `jumbo_chunk_count` | chunks with `jumbo: true` | WARN ≥ 1 |

**Acceptance criteria:**
- `_section_sharding()` skips silently (no section emitted) if cluster is not sharded
- Chunk distribution computed by grouping `config.chunks` by `shard` field
- `chunk_imbalance_ratio` WARNING if > 1.5×, CRITICAL if > 3×
- Jumbo chunks flagged with finding: `"X jumbo chunk(s) detected — balancer cannot split these"`
- `SECTION_TIER["Sharding"] = "P2"` added to `html_reporter.py`
- Works when agent is connected to `mongos`; skips if connected to a replica set primary

---

### BL-109 · Monitoring alert coverage quality
**Priority:** P2 | **Size:** M | **Epic:** 9 | **Section:** §11 Alerting Coverage (NEW)

**Story:** As a DBA, I want the health check to evaluate whether the key health
indicators it collects are also covered by the cluster's alerting configuration so I can
identify monitoring blind spots.

**New section:** §11 Alerting Coverage — consequence tier P2 (Degraded: gaps in
alerting mean issues won't be caught until they cause impact).

**Implementation approach:** The agent cannot directly query the customer's alerting
system (PagerDuty, OpsGenie, Datadog, MongoDB Ops Manager alerts). Instead, this section
compares the current health check findings against a configurable checklist of
"should-be-alerted" conditions.

**Config-driven checklist** (`config/alert_checklist.yaml`):
```yaml
expected_alerts:
  - metric: disk_used_pct
    threshold: 80
    description: "Disk usage > 80%"
  - metric: oplog_window_hours
    threshold: 24
    description: "Oplog window < 24h"
  - metric: replication_lag_max_sec
    threshold: 30
    description: "Replication lag > 30s"
  - metric: cache_hit_ratio_pct
    threshold: 90
    description: "Cache hit ratio < 90%"
```

For each expected alert: if the health check finds a breach on that metric AND severity ≥ WARNING,
the alert is likely covered. If the check finds a breach but the operator says "we have alerts",
note as covered. If no breach in this run, mark as "untested (metric OK this run)".

**Acceptance criteria:**
- New `config/alert_checklist.yaml` with default checklist of 5–8 critical metrics
- `_section_alerting_coverage()` compares current run breaches against checklist
- Output: `covered`, `gap`, or `untested` per checklist item
- Finding text for gaps: `"No alert configured for disk_used_pct > 80% — add an alert in your monitoring tool"`
- Severity WARNING if ≥ 1 critical metric has no alert coverage
- `SECTION_TIER["Alerting Coverage"] = "P2"` added to `html_reporter.py`
- Section gracefully skips if `config/alert_checklist.yaml` is absent

---

## Epic 10 — Report UI/UX Polish

*Goal: apply professional database health-check UI/UX standards — the report must be
as readable as Datadog or PagerDuty, actionable at a glance, and accessible to
non-expert stakeholders.*

Review basis: full HTML audit of `fleet_2026-03-29_08-24-11.html` and `html_reporter.py`
against Datadog, New Relic, and MongoDB Atlas UI conventions (2026-03-29).

---

### BL-110 · Copy-to-clipboard for Action Plan commands
**Priority:** P1 | **Size:** S

**Story:** As a DBA, I want a one-click copy button next to each `createIndex` /
`dropIndex` command in the Action Plan table so I can paste it directly into mongosh
without selecting monospace text by hand.

**Current state:** Commands are rendered in `<code class="rec-action">` with
`overflow-wrap: break-word` — readable but not interactive.

**Design:**
- Each action cell gets a small copy icon (📋 SVG or Unicode) absolutely positioned
  top-right of the `<code>` block
- `navigator.clipboard.writeText()` on click; button text briefly changes to "✓ Copied"
  for 1.5 s then reverts (pure JS, no dependencies)
- Graceful degradation: button hidden via `@supports` if Clipboard API unavailable

**Acceptance criteria:**
- Copy button renders in Action Plan table alongside every action cell
- Click copies the raw command text (no surrounding HTML) to clipboard
- "Copied ✓" feedback lasts 1.5 s
- Works in Safari, Chrome, Firefox latest
- No visible button when `window.isSecureContext === false` (http)

---

### BL-111 · Active Alerts — jump-to-section links
**Priority:** P1 | **Size:** S

**Story:** As a DBA reviewing the report, I want each alert card in the Active Alerts
section to have a "View details →" link that scrolls directly to the corresponding
section card so I can immediately investigate without scrolling manually.

**Current state:** Alert boxes show section name and first finding but no navigation
link. The sidebar nav provides a global list, but not from within each alert.

**Design:**
- Each `.alert` box gets a small "View section →" anchor at bottom-right corner
- Anchor `href` points to the section's anchor id (e.g., `#sec-replication`)
- Smooth scroll via existing `scrollIntoView({ behavior: 'smooth' })` JS
- Text: `View →` (compact), coloured with the alert's severity colour

**Acceptance criteria:**
- Every non-OK section alert box has a functioning "View →" link
- Click scrolls the page to the correct section card
- Link is visually consistent (uses `var(--t3)` normal, severity colour on hover)

---

### BL-112 · Fleet summary — aggregate fleet score + critical cluster banner
**Priority:** P1 | **Size:** S

**Story:** As a fleet operator, I want a prominently displayed overall fleet health
score and a banner that lists any CRITICAL clusters at the top of the Fleet Summary
tab so I know immediately whether I need to act.

**Current state:** Fleet summary shows a table sorted by score, but there is no
aggregate fleet score or "X clusters need immediate attention" call-out.

**Design — two additions to `_build_summary_panel()`:**

1. **Fleet aggregate score** — `min(scores)` for worst-case, displayed next to the
   title with the `.fleet-score-{ok|warn|crit}` badge already defined in CSS

2. **Critical banner** — if any cluster is CRITICAL, show a red alert bar above the
   table: `"⚠ 1 cluster requires immediate attention — {name}: {top_issue}"`

**Acceptance criteria:**
- Fleet aggregate score badge visible in summary header
- Critical banner appears when ≥ 1 cluster is CRITICAL; hidden otherwise
- Both elements update when switching between fleet runs (JS state preserved)
- No change to per-cluster view

---

### BL-113 · Score ring at top of sidebar (above nav groups)
**Priority:** P1 | **Size:** S

**Story:** As a DBA reading the report, I want the health score prominently displayed
near the top of the sidebar (below cluster name) so I can see the verdict immediately
without scrolling to the bottom of the nav.

**Current state:** The score ring is in `.sidebar-score` at the bottom of the sidebar,
appended with `margin-top: auto`. On long reports with many nav items, the score may
be pushed off-screen or require scrolling.

**Design:**
- Move the `.sidebar-score` block to immediately below `.sidebar-top`
  (before the nav groups)
- Remove `margin-top: auto`; add `margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 14px;`
- Increase score ring from 48px to 56px; font-size from 14px to 16px for legibility
- Keep the ring at the bottom of the sidebar as a secondary visual if room permits,
  OR remove the duplicate

**Acceptance criteria:**
- Score ring visible in sidebar without scrolling on a standard 1080p display
- Ring size 56px, score number 16px, both readable against dark background
- No overlap with cluster name / timestamp above

---

### BL-114 · Trend arrows on metric cards (vs prior baseline run)
**Priority:** P1 | **Size:** M

**Story:** As a DBA, I want each metric card to show a small trend arrow (↑↓→)
comparing the current value to the previous run's baseline mean so I can spot
deteriorating metrics before they breach thresholds.

**Current state:** `BaselineManager` stores rolling history but the report only uses
it for severity assessment — the raw direction is not surfaced in the UI. Metric cards
show static value + threshold with no historical context.

**Design:**
- Add optional `trend` field to `Signal` dataclass: `"up" | "down" | "stable" | None`
- `HealthCheckRunner` sets `sig.trend` when the metric is tracked by `BaselineManager`
  and `run_count >= COLD_START_RUNS`:
  - `up` if current > baseline_mean × 1.1
  - `down` if current < baseline_mean × 0.9
  - `stable` otherwise
- HTML renderer adds a tiny trend span to `.metric-sub`:
  - ↑ red for `higher-is-worse` up, green for `lower-is-worse` up
  - ↓ green for `higher-is-worse` down, red for `lower-is-worse` down
  - → gray for stable
- During cold-start period, trend is None and no arrow is shown

**Acceptance criteria:**
- Trend arrow visible on metric cards for tracked metrics after ≥ 3 runs
- Arrow colour reflects whether the direction is good or bad for that metric
- Cold-start clusters show no trend arrows
- Signal dataclass change is backwards-compatible (trend defaults to None)

---

### BL-115 · Replication lag human-readable duration
**Priority:** P1 | **Size:** S

**Story:** As a DBA, I want the replication lag signal to display as "2h 30m" or
"45s" rather than raw seconds so I can instantly gauge urgency without mental
arithmetic.

**Current state:** `replication_lag_max_sec` signal value is e.g. `9000` with unit
`seconds`. The metric card shows `9,000 seconds`.

**Implementation:**
- Add a `_fmt_duration(seconds: int) -> str` helper to `health_check_runner.py`:
  - < 60 → `"{s}s"`
  - < 3600 → `"{m}m {s}s"`
  - else → `"{h}h {m}m"`
- Use this as the `unit` field (or a separate `display_value` field on Signal)
- Alternatively: format in the HTML renderer's `_fmt()` when `sig.unit == "seconds"` and
  `sig.name == "replication_lag_max_sec"` — simpler, no model change

**Acceptance criteria:**
- Metric card shows "2h 30m" for 9000 seconds, "45s" for 45 seconds
- Threshold comparison still uses raw seconds internally
- Findings text also uses formatted duration

---

### BL-116 · Action Plan — group recommendations by priority tier
**Priority:** P1 | **Size:** S

**Story:** As a DBA, I want the Action Plan table to visually group recommendations
by priority tier (P0/P1/P2/P3/P4) with a tier header row so I can immediately focus
on critical items without scanning the entire list.

**Current state:** Recommendations are sorted by priority but rendered as a flat list
of table rows with no tier-level grouping. With 5+ recommendations it becomes a wall
of rows.

**Design:**
- Insert a shaded `<tr>` separator row at each tier boundary:
  `<tr class="tier-header"><td colspan="5"><span class="rec-p rp{N}">P{N}</span> {tier_label} — {consequence}</td></tr>`
- CSS for `.tier-header td`: `background: var(--surface2); padding: 6px 10px;`
- Only show tier header rows for tiers that have ≥ 1 recommendation
- Consequence text from `_TIER_LABEL` dict

**Acceptance criteria:**
- Tier header rows visible between P0→P1, P1→P2 boundaries etc.
- Tiers with no recommendations produce no header row
- Table still scrollable horizontally on narrow viewports

---

### BL-117 · Fix `<details>` accessibility — inline summary text, not CSS `::before`
**Priority:** P1 | **Size:** S

**Story:** As a screen reader user, I want the collapsible "Show details / Hide
details" toggle in section cards to be readable by assistive technology so the report
is WCAG 2.1 AA accessible.

**Current state:** `_section_card()` emits `<details><summary></summary>...</details>`
with an empty `<summary>`. The visible "▶ Show details" text is injected by
`.findings-details > summary::before { content: "▶  Show details"; }`. Screen readers
read `<summary>` as empty and the `::before` content may or may not be read depending
on the AT.

**Fix:**
- Change `f'<summary></summary>'` to `f'<summary>Show {len(detail_lines)} detail{"s" if len(detail_lines) != 1 else ""}</summary>'`
- Remove `::before` / `[open]::before` content CSS
- Add `list-style: none` to suppress the default triangle marker
- Replace with an explicit `::marker { content: ""; }` + custom arrow using
  `.findings-details > summary::after` (or inline SVG in `<summary>`)
- Add `aria-label` to `<details>` for AT context

**Acceptance criteria:**
- `<summary>` has meaningful text content ("Show 3 details" / "Hide 3 details")
- Toggle text updates between open/closed states via JS `toggle` event listener
- CSS `::before` content removed (no duplication)
- VoiceOver / NVDA reads the toggle correctly

---

### BL-118 · Light mode / auto theme (prefers-color-scheme)
**Priority:** P2 | **Size:** M

**Story:** As a DBA sharing the report with a manager or customer who uses a light OS
theme, I want the report to automatically switch to a high-contrast light colour
palette so it is readable without a dark display.

**Current state:** The report uses a single fixed dark theme with no media query.

**Design:**
- Add `@media (prefers-color-scheme: light)` block to `_CSS` overriding all CSS
  variables:
  ```
  --bg: #f8fafc;  --surface: #ffffff;  --surface2: #f1f5f9;
  --border: rgba(0,0,0,0.09);  --border-em: rgba(0,0,0,0.18);
  --t1: #0f172a;  --t2: #475569;  --t3: #94a3b8;
  --red: #dc2626;  --amber: #d97706;  --green: #059669;  --blue: #2563eb;
  ```
- All severity tints (`--red-bg`, `--amber-bg`, etc.) also adjusted for light mode
- Manual toggle button (🌙/☀) in the sticky bar to override system preference;
  stores choice in `localStorage`

**Acceptance criteria:**
- Report renders correctly in both dark and light OS themes
- All text passes WCAG AA contrast ratio in both modes
- Manual toggle persists across page reload (localStorage)
- Code blocks and metric values remain legible in light mode

---

### BL-119 · Print-friendly CSS for single-cluster report
**Priority:** P2 | **Size:** S

**Story:** As a DBA, I want to print or save-as-PDF the health check report and get a
clean, readable document with no sidebar, no sticky bars, and no dark background so I
can share it with stakeholders who prefer a PDF attachment.

**Current state:** No `@media print` rules exist. Printing produces a dark-background
document with the sidebar cramping the main content area.

**Design — `@media print` rules:**
- `.sidebar`, `.sticky-bar`, `.cluster-tabs` → `display: none`
- `.layout` → `display: block`
- `.main` → `max-width: none; padding: 20px`
- Body `background` → white; `color` → black
- Section cards: remove coloured left-border; replace with black top-border
- Metric grid: 3-column fixed layout
- Add `page-break-inside: avoid` on `.section`, `.rec-item`
- Action Plan table: full width, no overflow
- Footer: `display: block; text-align: left`

**Acceptance criteria:**
- `File → Print → Save as PDF` produces a clean black-on-white document
- All sections, metric grids, and recommendations are visible
- No sidebar, no sticky bar, no dark backgrounds
- Tested in Chrome and Safari print preview

---

### BL-120 · Metric headroom indicator — safe distance to threshold on OK cards
**Priority:** P2 | **Size:** S

**Story:** As a DBA, I want metric cards that are currently healthy to show how much
headroom remains before they breach their threshold so I can identify metrics trending
toward a problem before they hit WARNING.

**Current state:** OK metric cards show value and unit. The threshold is only shown
when breached. A metric at 78% disk with an 80% warning threshold looks identical to
a metric at 30% disk — no sense of proximity.

**Design:**
- For OK metrics with a threshold, add a thin progress bar below the value:
  `width = (value / threshold) × 100%` (capped at 99%)
  - 0–60% → `var(--green-border)`
  - 60–80% → `var(--amber-border)`
  - 80–99% → coloured amber/red to signal "approaching threshold"
- For `lower-is-worse` metrics (cache hit ratio, oplog window), invert: bar fills
  from right, shows safe margin above threshold
- Progress bar: 3px tall, border-radius 2px, full-width within the card
- Add small text below: `{headroom}% headroom` or `{delta} below threshold`

**Acceptance criteria:**
- Progress bar visible on all non-breached metrics that have a threshold
- Bar colour transitions correctly across the three zones
- `lower-is-worse` metrics show inverted representation
- Breached metrics retain existing red/amber border — no progress bar
- Renders correctly at minmax(155px) card width (no overflow)

---

### BL-121 · Placeholder sections — collapse or visually de-emphasise when OM not configured
**Priority:** P2 | **Size:** S

**Story:** As a DBA running without Ops Manager, I want the "Connections &
Concurrency" and "Infrastructure" sections (which are OM-dependent) to be visually
de-emphasised or collapsed by default so they don't consume space and draw attention
away from actionable sections.

**Current state:** Placeholder sections render as full-height section cards with
"Not available" tag, a bullet list of unavailable metrics, and a backlog reference.
They occupy as much vertical space as real sections and appear in the nav with a grey
dot — fine for development visibility but visually noisy for production reports.

**Design:**
- Replace the current placeholder card with a compact single-line entry:
  `<div class="placeholder-stub">Connections & Concurrency — not available (OM required) <a href="#" class="pl-expand">Show details</a></div>`
- Clicking "Show details" expands inline to the current full placeholder content
- Nav sidebar: greyed-out nav items for placeholder sections, smaller font, italics,
  no dot — clearly secondary
- `--placeholder-stub-bg: var(--surface)` with dashed border for quick visual ID

**Acceptance criteria:**
- Placeholder sections default to single-line stub on page load
- "Show details" expands to full placeholder content
- Nav items for placeholder sections are visually distinct from real sections
- Layout change does not affect sections that have real data

---

### BL-122 · Historical score sparkline per cluster in Fleet Summary
**Priority:** P2 | **Size:** M

**Story:** As a fleet operator, I want each cluster row in the Fleet Summary table to
show a small sparkline of the last 5–10 health scores so I can see at a glance whether
a cluster is stable, improving, or trending downward.

**Current state:** The Fleet Summary table shows only the current run's score. There
is no historical context. `BaselineManager` stores per-run metrics but not the
aggregate score per run.

**Design:**
- Store aggregate health score in `agent_memory.health_baselines` alongside metric
  history: add `"score_history": [list of last 10 scores]` to the baseline document
- `_build_summary_panel()` reads score history from report metadata or from a separate
  call to `BaselineManager`
- Render a 60×20px inline SVG sparkline in the Score column: polyline connecting the
  last N scores, coloured green/amber/red based on the trend direction
- Latest score shown as the text value next to the sparkline

**Implementation note:** Score history requires `HealthCheckRunner` to pass the
computed score to `BaselineManager.record_from_report()`, or a second upsert after
`_health_score()` is called.

**Acceptance criteria:**
- Score sparkline visible in Fleet Summary after ≥ 2 runs per cluster
- Sparkline renders within 60×20px without distorting the table row height
- Flat or rising line coloured green; declining line coloured amber/red
- Fallback: current score as plain text if < 2 history points

---

### BL-123 · OM-based cluster auto-discovery
**Priority:** P1 | **Size:** M | **Epic:** 9

**Story:** As a PS engineer deploying the agent at a customer site, I want the agent
to discover all monitored clusters automatically from Ops Manager so I only need to
provide the OM URL and API credentials — no manual YAML cluster list required.

**Customer ask reduced to:**
1. OM URL (e.g. `http://ops-manager.internal:8080`)
2. OM API keypair — two options:
   - **Global** (preferred for PS): Admin → General → Global API Keys → Create, role `Global Read Only` — works across all projects with no per-project setup
   - **Project-scoped**: Account → Access Manager → API Keys, role `Project Read Only` — must be added to each project individually
3. Network path to OM (direct, VPN, or bastion tunnel)

**Discovery flow:**

```
GET /api/public/v1.0/groups
  → for each group:
GET /api/public/v1.0/groups/{id}/hosts
  → extract: hostname, port, replicaSetName, typeName (PRIMARY/SECONDARY)
  → build URI: mongodb://{primary_host}:{port}/?replicaSet={rs}&directConnection=true
  → upsert into config monitored_clusters[]
```

**Implementation:**
- New `src/utils/om_discovery.py` — `OpsManagerDiscovery(url, public_key, private_key)`
  - `discover_clusters() -> List[ClusterConfig]`
  - Uses `requests` with HTTP Digest auth (already a dependency via mcp)
  - Groups hosts by `replicaSetName`; picks `typeName == "PRIMARY"` as the connection target
  - Falls back to any available member if no PRIMARY found (e.g. cluster mid-election)
- `config_loader.py` gains `--discover-from-om` flag (and `OM_AUTO_DISCOVER=true` env var)
  - When set, calls `OpsManagerDiscovery.discover_clusters()` and merges into `monitored_clusters`
  - Discovered clusters tagged `{om: true}` to distinguish from manually configured ones
  - Writes discovered list to `config/agent_config.yaml` (with confirmation prompt in interactive mode)
- `main_agentic.py`: if `monitored_clusters` is empty and OM is configured, auto-discover
  before running health check

**Acceptance criteria:**
- `python src/main_agentic.py --health-check --discover-from-om` discovers all RS primaries
  from the configured OM instance without any manual cluster config
- Outputs discovered cluster list to console before starting health check
- Graceful failure: if OM unreachable or 401, falls back to YAML-configured clusters with a warning
- Duplicate URIs are not added (idempotent merge)
- Works with OM 6.0 and 7.0 API; Atlas-managed deployments not in scope (see BL-053)

---

### BL-124 · WiredTiger engine pressure — tickets & dirty ratio
**Priority:** P1 | **Size:** S | **Epic:** 1 | **Section:** §8 Operations

**Story:** As a DBA, I want the Operations section to surface WiredTiger engine pressure
signals (read/write ticket availability and dirty cache ratio) so I can detect imminent
throughput collapse even when CPU and memory look normal.

**Context:** WiredTiger uses a ticket-based concurrency control (default 128 read + 128
write). When available tickets approach 0, new operations queue and the database stalls.
Similarly, when dirty data exceeds ~20% of the WT cache, user threads are drafted into
page eviction, causing severe latency spikes. Both conditions are invisible to CPU/memory
monitoring and are a leading cause of unexplained production slowdowns.

Note: §10 Connections already reports `tickets_reads` and `tickets_writes` as remaining
counts, but they lack the engine-pressure framing and dirty ratio context. This BL
consolidates engine health into §8 where serverStatus data is already available.

**Data source:** `serverStatus` — already fetched in `_section_operations()`.

**serverStatus paths:**
- `wiredTiger.concurrentTransactions.read.available` — remaining read tickets
- `wiredTiger.concurrentTransactions.write.available` — remaining write tickets
- `wiredTiger.concurrentTransactions.read.totalTickets` — max read tickets (128 default)
- `wiredTiger.concurrentTransactions.write.totalTickets` — max write tickets (128 default)
- `wiredTiger.cache["tracked dirty bytes in the cache"]` — current dirty bytes
- `wiredTiger.cache["maximum bytes configured"]` — max cache size

**Implementation:**
- Compute `dirty_ratio = dirty_bytes / max_bytes`
- Compute `read_ticket_pct = read_available / read_total * 100`
- Compute `write_ticket_pct = write_available / write_total * 100`
- Add signals: `wt_dirty_ratio_pct`, `wt_read_tickets_available`, `wt_write_tickets_available`
- Add to `_BELOW_THRESHOLD_IS_BAD` in all 3 files (ticket signals — low is bad)

**Acceptance criteria:**
- Signal `wt_dirty_ratio_pct` with threshold 20%; WARNING at >5%, CRITICAL at >20%
- Signal `wt_read_tickets_available` with threshold 10; WARNING at <20, CRITICAL at <10
- Signal `wt_write_tickets_available` with threshold 10; WARNING at <20, CRITICAL at <10
- Finding text explains the consequence: "User threads participate in eviction above 20%
  dirty ratio, causing request latency spikes"
- Recommendation generated when CRITICAL: "Investigate write-heavy workloads or increase
  WiredTiger cache size"
- Gracefully skips if `wiredTiger` key is absent from serverStatus (e.g. non-WT engine)

---

### BL-125 · Plan cache stats audit on low hit rate
**Priority:** P1 | **Size:** M | **Epic:** 1 | **Section:** §5 Query Performance / §8 Operations

**Story:** As a DBA, when the plan cache hit rate is low (<80%), I want the report to
automatically drill into `$planCacheStats` for the affected collections and identify
whether query shape instability or cache eviction is the root cause, so I get an
actionable diagnosis instead of just a metric.

**Context:** BL-103 added `plan_cache_hit_rate_pct` to §8 Operations. A 0% hit rate
means every query re-plans — this is expensive and often caused by unstable query shapes
(e.g. dynamically constructed filters with varying field sets) or excessive candidate
plans triggering cache eviction. The raw percentage alone doesn't tell the DBA *why*.

**Data source:** `db.<collection>.aggregate([{$planCacheStats: {}}])` — available since
MongoDB 4.2, well within our 8.0 target. Requires the `planCacheRead` privilege
(included in the `dbAdmin` and `clusterMonitor` roles).

**Trigger condition:** `plan_cache_hit_rate_pct < 80` (already detected in §8).

**Data flow:** §5 Query Performance already identifies the top slow collections via
`_top_slow_collections(slow_queries)`. These are the natural candidates for plan cache
audit — no additional collection discovery needed.

**Implementation:**
- When plan cache hit rate < 80%, call `$planCacheStats` on top 3 slow collections
  (from §5 slow query list)
- For each collection, extract:
  - Total cached plan entries
  - Entries with >3 candidate plans (indicates query optimizer indecision)
  - Most common query shape hash (indicates which shapes dominate the cache)
- Add finding to §8 Operations or §5 Query Performance (TBD — wherever it fits better)
- Use MCP `aggregate` tool (already available) — no new data access path needed

**Acceptance criteria:**
- When `plan_cache_hit_rate_pct < 80`, report includes plan cache audit for top 3 slow
  collections
- Finding identifies: number of cached entries, entries with >3 candidate plans,
  and whether cache is being evicted (entries < expected based on query diversity)
- Recommendation: "Stabilise query shapes" if high candidate plan count; "Increase
  planCacheSize" if eviction detected; "Review index strategy" if plans are suboptimal
- Gracefully skips if `$planCacheStats` returns an error (insufficient privileges)
- Does NOT run when hit rate >= 80% (avoid unnecessary overhead)

---
