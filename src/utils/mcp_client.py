"""Synchronous wrapper around the MongoDB MCP Server.

Uses a background thread with a single asyncio.run() call so that
anyio cancel scopes are always entered and exited within the same task.
"""

import asyncio
import json
import logging
import os
import queue
import threading
from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

NODE_PATH = os.path.expanduser("~/.nvm/versions/node/v24.14.0/bin/node")
MCP_SERVER_PATH = os.path.expanduser(
    "~/.nvm/versions/node/v24.14.0/bin/mongodb-mcp-server"
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
