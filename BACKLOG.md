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
| BL-021 | Baseline-aware severity assessment | P0 | M | 3 | 🔲 |
| BL-071 | Environment variable + secret config | P0 | S | 8 | 🔶 Partial |
| BL-032 | LangChain multi-LLM backend | P0 | M | 4 | ✅ Done |
| BL-010 | Health check pipeline | P0 | L | 2 | ✅ Done |
| BL-011 | Configurable scheduler | P0 | L | 2 | 🔲 |
| BL-030 | Structured tool output (typed) | P0 | L | 4 | 🔲 |
| BL-070 | Docker Compose deployment | P0 | L | 8 | 🔲 |
| BL-009 | Operations health section (serverStatus metrics) | P1 | M | 1 | ✅ Done |
| BL-013 | Connection pool health section | P1 | M | 1 | 🔲 |
| BL-014 | Scan & sort analysis in Query Performance | P1 | S | 1 | ✅ Done |
| BL-015 | OS / infrastructure metrics (CPU, IOPS, disk queue) | P1 | L | 1 | 🔲 |
| BL-005 | Current operations tool | P1 | S | 1 | 🔲 |
| BL-006 | Profiler configuration check | P1 | S | 1 | 🔲 |
| BL-007 | Duplicate/redundant index detection | P1 | S | 1 | 🔲 |
| BL-023 | Confidence scoring on recommendations | P1 | S | 3 | ✅ Done |
| BL-074 | PS delivery runbook (< 30 min) | P1 | S | 8 | 🔲 |
| BL-008 | Aggregation pipeline analysis | P1 | M | 1 | 🔲 |
| BL-012 | Trend comparison in scheduled runs | P1 | M | 2 | 🔲 |
| BL-022 | Webhook / notification output | P1 | M | 3 | 🔲 |
| BL-031 | Automatic tool parameter chaining | P1 | M | 4 | 🔲 |
| BL-060 | HTML report output | P1 | M | 7 | ✅ Done |
| BL-073 | Secret management integration | P1 | M | 8 | 🔲 |
| BL-050 | Multi-cluster support | P1 | L | 6 | 🔶 Partial |
| BL-033 | ESR index order validation | P2 | S | 4 | 🔲 |
| BL-041 | Approval-gated profiler config | P2 | S | 5 | 🔲 |
| BL-052 | Immutable audit trail | P2 | S | 6 | 🔲 |
| BL-061 | Markdown report output | P2 | S | 7 | ✅ Done |
| BL-075 | Data sovereignty mode | P2 | S | 8 | 🔲 |
| BL-072 | Non-Docker quickstart script | P2 | M | 8 | 🔲 |
| BL-040 | Approval-gated index creation | P2 | L | 5 | 🔲 |
| BL-051 | REST API + Web UI | P2 | XL | 6 | 🔲 |
| BL-042 | Drop unused index (approval-gated) | P3 | S | 5 | 🔲 |
| BL-053 | MongoDB Atlas integration | P3 | L | 6 | 🔲 |

**Done:** 12 items (BL-020, BL-001, BL-002, BL-003, BL-004, BL-060, BL-010, BL-032, BL-061, BL-023, BL-014)
**Partial:** 2 items (BL-050 — within-cluster multi-DB done; BL-071 — LLM+MongoDB env vars done, full coverage pending)
**P0:** 4 remaining — scheduler (BL-011), baseline severity (BL-021), typed output (BL-030), Docker (BL-070)
**P1:** 15 items — high-value once P0 is in place (includes new BL-014, BL-015)
**P2–P3:** 9 items — important but not blocking
**Total:** 39 items across 8 epics (11 done, 2 partial, 26 remaining)

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
**Status:** 🔶 Partial — within-cluster multi-database discovery is done; multi-cluster registration is not.

**Story:** As a DBA managing more than one MongoDB cluster, I want to run a health
check against any registered cluster by name so I don't need to edit config files.

**Done (v0.3.0):**
- `_section_query_performance` iterates all user databases discovered via `list-databases` —
  no database name is hardcoded. Deploy to any cluster; all databases are picked up automatically.
- `_top_slow_collections` returns `{"db", "collection"}` dicts so the correct database is used
  in §6 index checks regardless of which database a slow query came from.

**Remaining:**
- `monitored_clusters` list in config replaces single `monitored_cluster` URI
- Each cluster has a `name`, `uri`, and optional `tags` (e.g. `production`, `staging`)
- CLI accepts `--cluster <name>` flag
- Memory store scoped per cluster URI (investigations tagged with cluster name)
- Health check report header includes cluster name

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
- `docker-compose.yml` defines four services:
  - `agent` — Python app image; all LLM providers supported via env vars
  - `mongo-memory` — MongoDB 8.0, port 27017, agent memory store
  - `mongo-monitored` — MongoDB 8.0, port 27018, for local dev/demo only
    (production: replaced by customer's `AGENT_MONGO_CLUSTER` env var)
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
