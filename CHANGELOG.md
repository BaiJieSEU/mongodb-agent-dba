# Changelog

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
