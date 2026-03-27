"""Synchronous wrapper around the MongoDB MCP Server.

Uses a background thread with a single asyncio.run() call so that
anyio cancel scopes are always entered and exited within the same task.
"""

import asyncio
import json
import logging
import os
import queue
import re
import shutil
import threading
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Resolve Node and MCP server paths:
# 1. Explicit env var override (Docker / CI)
# 2. PATH lookup (npm global install, Docker image)
# 3. NVM local dev fallback
NODE_PATH = (
    os.environ.get("AGENT_NODE_PATH")
    or shutil.which("node")
    or os.path.expanduser("~/.nvm/versions/node/v24.14.0/bin/node")
)
MCP_SERVER_PATH = (
    os.environ.get("AGENT_MCP_SERVER_PATH")
    or shutil.which("mongodb-mcp-server")
    or os.path.expanduser("~/.nvm/versions/node/v24.14.0/bin/mongodb-mcp-server")
)

_STOP = object()       # sentinel: end the session
_LIST_TOOLS = object() # sentinel: list available tools


class MCPClient:
    """Keeps one MCP server process alive for one investigation session.

    Usage::

        with MCPClient("mongodb://localhost:27018") as client:
            result = client.call_tool("list-collections", {"database": "testdb"})
    """

    def __init__(self, mongodb_uri: str, read_only: bool = True):
        self.mongodb_uri = mongodb_uri
        self.read_only = read_only
        self._task_q: queue.Queue = queue.Queue()
        self._ready_q: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None

    # ── context manager ────────────────────────────────────────────────────────

    def __enter__(self) -> "MCPClient":
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        result = self._ready_q.get(timeout=30)
        if isinstance(result, Exception):
            raise result
        return self

    def __exit__(self, *args) -> None:
        self._task_q.put((_STOP, None, None))
        if self._thread:
            self._thread.join(timeout=10)

    # ── background thread ──────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        try:
            asyncio.run(self._session_loop())
        except Exception as e:
            if self._ready_q.empty():
                self._ready_q.put(e)

    async def _session_loop(self) -> None:
        """Full MCP session lifecycle running inside one asyncio.run() call."""
        server_args = [MCP_SERVER_PATH, "--connectionString", self.mongodb_uri]
        if self.read_only:
            server_args.append("--readOnly")

        server_params = StdioServerParameters(command=NODE_PATH, args=server_args)
        loop = asyncio.get_running_loop()

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Explicitly connect to MongoDB (required by this MCP server version)
                await session.call_tool("connect", {"connectionStringOrClusterName": self.mongodb_uri})
                logger.info("MCP session ready: %s", self.mongodb_uri)
                self._ready_q.put(True)

                while True:
                    sentinel, arguments, result_q = await loop.run_in_executor(
                        None, self._task_q.get
                    )

                    if sentinel is _STOP:
                        break

                    if sentinel is _LIST_TOOLS:
                        try:
                            res = await session.list_tools()
                            result_q.put(("ok", [t.name for t in res.tools]))
                        except Exception as exc:
                            result_q.put(("err", exc))
                    else:
                        # sentinel holds the tool name string
                        tool_name = sentinel
                        try:
                            mcp_result = await session.call_tool(tool_name, arguments)
                            result_q.put(("ok", mcp_result))
                        except Exception as exc:
                            result_q.put(("err", exc))

    # ── helpers ────────────────────────────────────────────────────────────────

    def _send(self, sentinel: Any, arguments: Dict[str, Any]) -> Any:
        result_q: queue.Queue = queue.Queue()
        self._task_q.put((sentinel, arguments, result_q))
        status, value = result_q.get(timeout=60)
        if status == "err":
            raise value
        return value

    @staticmethod
    def _parse_content(mcp_result: Any) -> List[str]:
        """Return all text content blocks as a list of strings."""
        blocks = []
        for content in mcp_result.content:
            if hasattr(content, "text") and content.text:
                blocks.append(content.text)
        return blocks

    # ── public sync API ────────────────────────────────────────────────────────

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool synchronously and return the parsed result."""
        mcp_result = self._send(tool_name, arguments)
        return self._parse_content(mcp_result)

    def list_tools(self) -> List[str]:
        return self._send(_LIST_TOOLS, {})

    def ping(self) -> bool:
        try:
            return len(self.list_tools()) > 0
        except Exception:
            return False

    # ── private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_names(blocks: List[str]) -> List[str]:
        """Extract name from 'Name: foo' or 'Name: foo, Size: ...' blocks."""
        return [b[5:].strip().split(",")[0].strip() for b in blocks if b.startswith("Name:")]

    @staticmethod
    def _parse_json_docs(blocks: List[str]) -> List[Dict[str, Any]]:
        """Parse find/aggregate result blocks — skip count header, parse remaining as JSON."""
        docs = []
        for b in blocks[1:]:
            try:
                docs.append(json.loads(b))
            except (json.JSONDecodeError, TypeError):
                pass
        return docs

    # ── typed tool methods ─────────────────────────────────────────────────────

    def list_databases(self) -> List[str]:
        """Return list of database names."""
        return self._parse_names(self.call_tool("list-databases", {}))

    def list_collections(self, database: str) -> List[str]:
        """Return list of collection names in a database."""
        return self._parse_names(self.call_tool("list-collections", {"database": database}))

    def find(
        self,
        database: str,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
        sort: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Run a find query and return parsed documents."""
        args: Dict[str, Any] = {"database": database, "collection": collection, "limit": limit}
        if filter:
            args["filter"] = filter
        if sort:
            args["sort"] = sort
        return self._parse_json_docs(self.call_tool("find", args))

    def db_stats(self, database: str) -> Dict[str, Any]:
        """Return db-stats for a database as a dict."""
        blocks = self.call_tool("db-stats", {"database": database})
        for b in blocks:
            if b.startswith("Statistics for database"):
                try:
                    return json.loads(b[b.index("{"):])
                except (ValueError, json.JSONDecodeError):
                    pass
        return {}

    def collection_storage_size(self, database: str, collection: str) -> float:
        """Return collection storage size in MB."""
        blocks = self.call_tool("collection-storage-size", {"database": database, "collection": collection})
        for b in blocks:
            m = re.search(r"is `([\d.]+)\s*(MB|KB|GB|bytes)`", b)
            if m:
                val, unit = float(m.group(1)), m.group(2)
                if unit == "KB":    return round(val / 1024, 3)
                if unit == "GB":    return round(val * 1024, 3)
                if unit == "bytes": return round(val / 1_048_576, 6)
                return round(val, 3)
        return 0.0

    def count(
        self,
        database: str,
        collection: str,
        filter: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Return document count for a collection."""
        args: Dict[str, Any] = {"database": database, "collection": collection}
        if filter:
            args["filter"] = filter
        blocks = self.call_tool("count", args)
        for b in blocks:
            m = re.search(r"Found ([\d,]+) documents", b)
            if m:
                return int(m.group(1).replace(",", ""))
        return 0

    def aggregate(
        self, database: str, collection: str, pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run an aggregation pipeline and return parsed documents."""
        blocks = self.call_tool("aggregate", {
            "database": database, "collection": collection, "pipeline": pipeline,
        })
        return self._parse_json_docs(blocks)

    def collection_indexes(self, database: str, collection: str) -> List[Dict[str, Any]]:
        """Return parsed index descriptors: [{"name": str, "fields": [str]}, ...]."""
        blocks = self.call_tool("collection-indexes", {"database": database, "collection": collection})
        indexes: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {}
        for block in blocks:
            if block.startswith("Field:"):
                current.setdefault("fields", []).append(block[6:].strip())
            elif block.startswith("Name:"):
                current["name"] = block[5:].strip().split(",")[0].strip()
                indexes.append(current)
                current = {}
        if current:
            indexes.append(current)
        return indexes

    def explain(self, database: str, collection: str, method: List[Dict[str, Any]]) -> str:
        """Return explain output as a string."""
        blocks = self.call_tool("explain", {
            "database": database, "collection": collection, "method": method,
        })
        return "\n".join(blocks)
