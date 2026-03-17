# Changelog

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
