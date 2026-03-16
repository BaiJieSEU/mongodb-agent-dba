# Changelog

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
