# Changelog

## [0.7.7] — 2026-03-25

### Summary
Three new health check items: agent/OM version in report header (BL-087), profiler
configuration check per database (BL-006), and redundant/duplicate index detection (BL-007).
Also fixed the in-memory sort finding incorrectly appending the targeting-ratio baseline note.

### Added
- `src/main_agentic.py` — `__version__ = "0.7.7"` constant.
- `src/models/health_check_report.py` — `agent_version` and `om_version` fields on
  `HealthCheckReport`; serialised to JSON when set.
- `src/utils/om_client.py` — `OMClient.get_version()`: hits `/api/public/v1.0/` root
  endpoint and returns the OM version string; None on failure.
- `src/agent/health_check_runner.py` — **BL-006**: `_section_query_performance()` now
  calls `db.command({"profile": -1})` for each user database via direct PyMongo; adds
  `profiler_disabled_dbs` and `profiler_high_slowms_dbs` signals + WARNING findings when
  profiler is off or `slowms > 100`.
- `src/agent/health_check_runner.py` — **BL-007**: `_section_index_usage()` detects
  redundant indexes (exact duplicates + left-prefix redundancies) using the key patterns
  already returned by `$indexStats`. Adds `redundant_indexes` signal and finding lines
  naming the redundant index and the compound index that covers it.
- `src/utils/html_reporter.py` — `_SIGNAL_LABELS` and `_METRIC_TOOLTIPS` entries for
  `redundant_indexes`, `profiler_disabled_dbs`, `profiler_high_slowms_dbs`.
- HTML report header now shows `Agent vX.Y.Z` (and `· OM <version>` when OM configured).

### Fixed
- `src/agent/health_check_runner.py` — in-memory sort count finding no longer appends the
  targeting-ratio baseline note (e.g. `(baseline: 1187.7)`); the baseline note now appears
  on its own line so the two findings are not conflated.

---

## [0.7.6] — 2026-03-25

### Summary
Fixed LLM recommendation quality (BL-034): recommendations no longer target healthy
signals or use a breached signal as a springboard to speculate about unrelated metrics.

### Fixed
- `src/agent/llm_recommender.py` — added CRITICAL RULE #3 to system prompt: do not
  recommend "investigate X" or "review X" where X has status="ok". Each action must
  directly address the specific breached signal(s) cited as evidence.
- LLM no longer generates "investigate lock wait %" when `lock_wait_pct=0` (ok), or
  "review cache hit ratio" when `wt_cache_hit_ratio=100%` (ok), even when
  `cluster_targeting_ratio` is breached in the same section.
- Cross-section reasoning focus tightened: patterns require MULTIPLE status="breached"
  signals, not one breached signal used to infer problems with healthy metrics.

---

## [0.7.5] — 2026-03-25

### Summary
Report polish: section group headers in the body, ⓘ coverage improvements, and
removal of remaining duplicate findings in §4 Storage and §8 Operations.

### Changed
- `src/utils/html_reporter.py` — `_build_content()`: added visual group headers
  ("Availability", "Resource Health", "Performance", "Index Advisory") between section
  groups in the main content area, matching the sidebar nav structure.
- `_METRIC_TOOLTIPS`: removed obvious ⓘ from `database_count` and `collection_count`;
  added `collscan_count`, `sort_stage_count`, `sort_spill_count`, `max_execution_ms`;
  updated `mongodb_version` tooltip with current MongoDB lifecycle info (7.0 LTS, 8.0 LTS).
- `src/agent/health_check_runner.py` — `_section_storage_stats()`: removed
  `collections_analysed` signal (duplicate of §1 collection count).
- `_section_operations()`: removed findings lines that duplicated metric cards
  (`Memory: X MB`, `Page faults: X`, `Global lock wait: X%`, `Index efficiency: X×`).
  Kept: throughput since restart, WiredTiger cache used/max MB (not in any card),
  in-memory sort count, and threshold-breach alert lines.

### Added (backlog)
- BL-085: Query Performance findings — structured readable layout (P1/S)
- BL-086: Metric tooltip context for non-breached signals — page faults, throughput (P2/S)
- BL-087: OM version and agent version in report header (P2/S)

---

## [0.7.4] — 2026-03-25

### Summary
Added ⓘ metric card tooltips with two-tier explanations: static definitions for all
known signals, and LLM-generated contextual interpretations for breached signals (BL-084).

### Added
- `src/models/health_check_report.py` — `Signal.tooltip: Optional[str]` field; serialised
  to JSON when set; used by HTML renderer to show LLM interpretation over static definition.
- `src/utils/html_reporter.py` — `_METRIC_TOOLTIPS` dict: 25 static one-liner definitions
  covering all signals in §1–§10. CSS-only ⓘ tooltip rendered on hover/focus — no
  JavaScript, self-contained HTML. Blue border + arrow pointer; 260px wide overlay.
- `src/agent/llm_recommender.py` — `LLMRecommender.enrich_signal_tooltips()`: collects
  all breached signals across sections, sends a single batched LLM call asking for a
  ≤25-word contextual interpretation per signal (citing the actual value), writes the
  result back to `Signal.tooltip` in-place. 45 s timeout; fails silently to static tooltip.
- `src/agent/health_check_runner.py` — `run()` now calls `enrich_signal_tooltips()` after
  `enrich()`, reusing the same `LLMRecommender` instance.

### Changed
- `html_reporter.py` — `_metric_grid()`: renders ⓘ icon next to metric label when
  `sig.tooltip` or `_METRIC_TOOLTIPS` entry exists. LLM tooltip takes precedence over
  static definition for breached signals.

---

## [0.7.3] — 2026-03-25

### Summary
Eliminated duplicate data between metric cards and findings across all sections (BL-081).
Extended signal label polish to §1 and §2.

### Changed
- `src/agent/health_check_runner.py` — `_section_cluster_overview()`: removed the
  redundant "N user database(s), M collection(s) total" line (duplicated metric cards)
  and the full per-database collection name list. Replaced with a single contextual line
  showing database names and collection counts — information not present in the cards.
- `_section_server_health()`: removed "MongoDB X.Y.Z · host · uptime" and
  "Filesystem disk: X GB used of Y GB (Z%)" findings — all values already in metric
  cards. Kept: host name (not in any card), APFS/fsUsedSize note, baseline cold-start
  note, threshold-breach alert line.
- `src/utils/html_reporter.py` — `_SIGNAL_LABELS`: extended to cover §1 and §2 signals:
  `database_count` → "Databases", `collection_count` → "Collections",
  `mongodb_version` → "Version", `uptime_hours` → "Uptime",
  `filesystem_disk_used_gb` → "Disk Used", `filesystem_disk_used_pct` → "Disk Used %".

---

## [0.7.2] — 2026-03-25

### Summary
Restructured HTML report sidebar navigation and content scroll order to match a
standard MongoDB DBA mental model (BL-082). Fixed missing Unused Indexes nav link.

### Changed
- `src/utils/html_reporter.py` — `_NAV_GROUPS`: replaced 4 groups (Overview,
  Performance, Reliability, Action) with 6 semantically correct groups:
  **Summary** (Cluster overview, Active alerts),
  **Availability** (Replication, Connections & concurrency),
  **Resource Health** (Server health, Storage, Infrastructure),
  **Performance** (Query performance, Operations),
  **Index Advisory** (Missing indexes, Unused indexes),
  **Action Plan** (Recommendations).
- `_build_content()`: content scroll order updated to match nav group top-to-bottom
  order so scrolling and clicking stay in sync.
- `_dot()`: removed stale `sec-indexes` combined-severity workaround; both index
  sections now resolve directly via their own `section_name` lookup.
- **Fixed**: Unused Indexes had no sidebar nav link — now has its own entry under
  Index Advisory.
- "Alerts" nav label renamed to "Active alerts" for clarity.

---

## [0.7.1] — 2026-03-24

### Summary
Improved HTML report readability for §9 Connections & Concurrency and §10 Infrastructure:
metric card labels are now human-friendly, and redundant findings text that duplicated
metric card values has been removed.

### Changed
- `src/utils/html_reporter.py`: added `_SIGNAL_LABELS` dict mapping signal names to
  display-friendly labels (e.g. `cpu_user_pct` → "CPU User %", `disk_iops_write` →
  "Disk Write IOPS", `total_connections` → "Connections"). Falls back to
  `.replace("_", " ").title()` for unlisted signals.
- `src/agent/health_check_runner.py` — `_section_infrastructure()`: removed findings
  lines that duplicated metric card values (CPU user %, I/O wait %, memory used %,
  disk write IOPS, disk write latency). Kept: primary hostname, disk partition name,
  and threshold-breach warning lines.
- `src/agent/health_check_runner.py` — `_section_connections()`: removed findings
  lines that duplicated metric card values (total connections, read/write ticket counts,
  lock queue depth). Kept: per-member breakdown table and threshold-breach warnings.

---

## [0.7.0] — 2026-03-24

### Summary
Added Ops Manager API integration, closing BL-013 (connection pool) and BL-015
(infrastructure metrics). Section 3 now shows real PRIMARY/SECONDARY state and
per-secondary replication lag. Two new sections added to the health check pipeline.

### Added
- `src/utils/om_client.py` — `OMClient`: read-only HTTP Digest auth wrapper for the
  OM Public API v1.0. Methods: `get_hosts()`, `get_host_measurements()`,
  `get_disk_name()`, `get_disk_measurements()`. All methods fail silently so OM
  being unreachable never blocks the health check.
- **Section 9 — Connections & Concurrency** (BL-013): polls all RS members via OM for
  `CONNECTIONS`, `TICKETS_AVAILABLE_READS/WRITE`, `GLOBAL_LOCK_CURRENT_QUEUE_TOTAL`.
  Shows per-member breakdown; warns on ticket exhaustion (< 10 remaining).
- **Section 10 — Infrastructure** (BL-015): pulls `PROCESS_NORMALIZED_CPU_USER`,
  `SYSTEM_CPU_IOWAIT`, `SYSTEM_MEMORY_USED/AVAILABLE`, `DISK_PARTITION_IOPS_WRITE`,
  and `DISK_PARTITION_LATENCY_WRITE` from the primary node via OM.
- `OMConfig` Pydantic model in `config_loader.py`; env vars `OM_URL`, `OM_GROUP_ID`,
  `OM_API_PUBLIC_KEY`, `OM_API_PRIVATE_KEY`. URL and group ID stored in
  `agent_config.yaml`; credentials always from env only.

### Changed
- **Section 3 — Replication Health**: if OM is configured, each RS member now shows
  `[REPLICA_PRIMARY]` / `[REPLICA_SECONDARY]` and per-secondary replication lag
  (`OPLOG_SLAVE_LAG_MASTER_TIME`) sourced from OM. Falls back to "set OM keys"
  message when OM is not configured.
- `config/agent_config.yaml`: added `ops_manager` block (url + group_id; no keys).
- `src/utils/html_reporter.py`: registered `Connections & Concurrency` and
  `Infrastructure` sections in `_SECTION_META`, `_NAV_GROUPS`, and `_build_content`;
  removed `_placeholder_section` call for BL-013.

---

## [0.6.0] — 2026-03-24

### Summary
Fixed a health check crash on zero-result full-scan queries and restored LLM enrichment
for qwen3:8b by disabling its built-in thinking mode. LLM recommendations now consistently
appear in every health check run.

### Fixed
- **`ZeroDivisionError` in `_build_recommendations`** — when a slow query returns 0
  documents (e.g. a no-match full scan), `examined / returned` crashed. Evidence string
  now shows `∞× (0 docs returned)` instead of raising.
- **LLM enrichment always timing out** — `qwen3:8b` has thinking mode on by default,
  generating a hidden `<think>…</think>` chain-of-thought block that consumed the entire
  60 s budget. `langchain_ollama` v1.0.1 does not expose a `think` parameter, so
  `_build_ollama()` in `llm_factory.py` now uses a direct `requests` call to the Ollama
  `/api/chat` endpoint with `"think": false`. Response time dropped from >60 s (timeout)
  to ~14 s; LLM enrichment now produces recommendations on every run.

### Changed
- `src/utils/llm_factory.py` — `_OllamaNoThinkRunnable` replaces `ChatOllama` for the
  Ollama provider; calls `/api/chat` directly with `think: false` and implements the same
  `invoke(prompt) -> str` interface expected by `LLMRecommender`.
- `config/agent_config.yaml` — monitored cluster updated to `ecommerce`
  (`mongodb://localhost:27018`); `local-rs1` and `local-rs2` entries removed.

---

## [0.3.0] — 2026-03-17

### Summary
Eliminated hardcoded database names so the health check works against any MongoDB
environment without code changes. Refactored the recommendation engine to use
structured data throughout — no string parsing of finding lines. Improved
recommendation quality: specific `createIndex` / `dropIndex` scripts with correct
field names and fully-qualified `db.collection` labels. Added `testUATdb` to the
demo scenario to validate multi-database discovery.

### Added
- `testUATdb` database in `create_demo_scenario.py` with two collections:
  - `inventory` (20k docs, no indexes) → triggers §5 WARNING + §6 CRITICAL
  - `customers` (15k docs, unused `email_1` index) → triggers §7 WARNING + P1 drop recommendation
- `HealthCheckRunner._SKIP_FIELDS` class-level frozenset — command-keyword filter used
  when extracting filter fields from profiler documents.
- `HealthCheckRunner._extract_filter_fields()` static method — extracts non-operator,
  non-command field names from a profiler command dict.

### Changed
- **`_section_query_performance(user_dbs)`** — now accepts the discovered database list
  and queries `system.profile` in every user database. No database name is hardcoded
  anywhere in the health check pipeline.
- **`_section_query_performance` doc parsing** — `db` extracted from `ns` field
  (`"testdb.orders"` → `db="testdb"`, `collection="orders"`); no hardcoded fallback.
- **`_top_slow_collections`** — return type changed from `List[str]` to
  `List[Dict[str, str]]` (`[{"db": ..., "collection": ...}]`) so the database is
  carried into §6 without re-discovery.
- **`_section_index_health(collections)`** — parameter changed to accept the new dict
  list; calls `collection-indexes` with the correct `db` for each entry. Collection
  labels in findings use `db.collection` format (e.g. `"testdb.orders"`).
- **`_section_index_usage`** — return type changed from `ReportSection` to
  `Tuple[ReportSection, List[Dict[str, Any]]]`; the second element is the structured
  unused-index list (fields: `db`, `collection`, `name`, `since`, `ops`).
- **`_build_recommendations`** — signature adds `unused_indexes: List[Dict]` parameter.
  Unused-index drop recommendations built directly from structured data — no string
  parsing of finding lines. For `createIndex` recs, iterates *all* slow queries for a
  collection (sorted by docs examined) to find the best entry with extractable filter
  fields, skipping aggregate-only profiler entries.
- Section name "Index Health" renamed to **"Missing Indexes"** throughout.
- Section name "Index Usage" renamed to **"Unused Indexes"** throughout.
- `run()` unpacks `(usage_section, unused_indexes)` tuple and passes `unused_indexes`
  to `_build_recommendations`.
- LLM model updated to `qwen3:8b` in `config/agent_config.yaml`.

### Fixed
- `createIndex` recommendations no longer show "Identify filter fields on orders …"
  when the top profiler entry is an aggregate command with no filter. The engine now
  scans all slow queries for the collection and picks the highest-examined find query
  with usable filter fields.
- Drop-index recommendations were previously derived by parsing `" → "` delimiters in
  finding strings (fragile). Now derived directly from the structured unused-index list.
- Collection field in `Recommendation` objects now uses `db.collection` format
  (`testdb.orders` instead of bare `orders`), making it unambiguous in the report.

---

## [0.2.0] — 2026-03-16

### Summary
Replaced the four hardcoded Python tool classes with the official MongoDB MCP Server.
All database operations on the monitored cluster now go through a single MCP subprocess
kept alive for the duration of each investigation session.

### Added
- `src/utils/mcp_client.py` — `MCPClient`: synchronous context-manager wrapper around
  the MongoDB MCP Server. Uses a background thread with `asyncio.run()` so that anyio
  cancel scopes are always entered and exited in the same task.
- `architecture.svg` — rendered architecture diagram (dark-mode SVG).
- Node.js dependency: `@mongodb-js/mongodb-mcp-server` (install globally with npm).
- Python dependency: `mcp` SDK (`mcp.ClientSession`, `mcp.client.stdio`).

### Changed
- `src/agent/intelligent_agentic_agent.py` — `execute_tool()` and all `_tool_*` helpers
  now delegate to `MCPClient.call_tool()` instead of calling Python classes directly.
  The MCP session is opened once per `investigate()` call and shared across all steps.
- `requirements.txt` — added `mcp` package; removed `pymongo` direct usage for the
  monitored cluster (memory store still uses PyMongo).
- `README.md` — updated architecture overview, infrastructure table, project structure,
  and MCP tool mapping table to reflect current state.
- `architecture_diagram.md` — replaced "Database Analysis Tools Layer" with
  "MCP Tool Execution Layer"; updated Technology Stack.

### Removed
- `src/tools/slow_query_fetcher.py` — superseded by MCP `find` on `system.profile`.
- `src/tools/query_explainer.py` — superseded by MCP `explain`.
- `src/tools/index_checker.py` — superseded by MCP `collection-indexes`.
- `src/tools/metadata_inspector.py` — superseded by MCP `list-collections` /
  `list-databases`.
- `src/tools/__init__.py` — tools package removed.
- `src/tools/recommendation_generator.py` — legacy file, unused in agentic system.

---

## [0.1.0] — 2026-02-XX

Initial release: memory-enhanced agentic DBA agent with four hardcoded Python tool
classes (`SlowQueryFetcher`, `QueryExplainer`, `IndexChecker`, `MetadataInspector`),
`AgentMemory` persistent storage, and Ollama/QWEN LLM integration.
