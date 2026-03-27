"""Intelligent Agentic MongoDB DBA Agent — MCP-powered tool execution"""

import logging
import time
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from utils.mongodb_client import MongoDBManager
from utils.config_loader import AppConfig
from utils.mcp_client import MCPClient
from utils.llm_factory import build_llm
from memory.agent_memory import AgentMemory, Investigation, PerformanceIssue

logger = logging.getLogger(__name__)


class IntelligentAgenticDBAAgent:
    """Intelligent AI Agent with semantic understanding and MCP-based tool execution"""

    def __init__(self, config: AppConfig, mongo_manager: MongoDBManager, cluster=None):
        self.config = config
        self.mongo_manager = mongo_manager

        # LLM — provider selected by config.llm.provider (or AGENT_LLM_PROVIDER env var)
        self.llm = build_llm(config)

        # Memory (agent store on port 27017)
        self.memory = AgentMemory(
            connection_string=config.mongodb.agent_store,
            database_name="agent_memory",
        )

        # Cluster targeting — defaults to first configured cluster
        if cluster is not None:
            self._cluster_uri = cluster.uri
            self._cluster_name = cluster.name
        else:
            self._cluster_uri = config.mongodb.monitored_cluster
            self._cluster_name = ""

        # MCP server targets the monitored cluster (port 27018)
        self._mcp_uri = self._cluster_uri

        # Tool registry — no more Python class handlers, execution goes via MCP
        self.tools = {
            "list_collections": {
                "description": "Shows what collections exist in a database with document counts and sizes",
                "use_when": "User wants to know about database structure, available collections, or collection metadata",
                "example_queries": ["what collections do I have", "show me my tables", "how many collections"],
            },
            "list_databases": {
                "description": "Shows available databases with basic statistics",
                "use_when": "User wants to know what databases are available or database-level information",
                "example_queries": ["what databases exist", "show me available databases"],
            },
            "fetch_slow_queries": {
                "description": "Identifies queries that are performing poorly or taking too long, from the MongoDB profiler",
                "use_when": "User reports performance problems, slowness, or wants optimization",
                "example_queries": ["database is slow", "find bottlenecks", "performance issues"],
            },
            "explain_query": {
                "description": "Analyzes the execution plan of a specific query to understand why it is slow",
                "use_when": "Need to understand why a specific query is slow after identifying it",
                "example_queries": ["why is this query slow", "analyze query performance"],
            },
            "check_indexes": {
                "description": "Lists existing indexes on a collection and identifies optimization opportunities",
                "use_when": "Need to review index coverage and suggest index improvements",
                "example_queries": ["optimize indexes", "what indexes do I have", "suggest index improvements"],
            },
        }

        # Active MCP client — set during investigate()
        self._mcp: Optional[MCPClient] = None

    # ── LLM helpers ────────────────────────────────────────────────────────────

    def clean_llm_response(self, response: str) -> str:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()

    def classify_user_intent(
        self, user_input: str, memory_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        memory_summary = ""
        if memory_context:
            recent_count = len(memory_context.get("recent_investigations", []))
            recurring_count = len(memory_context.get("recurring_issues", []))
            total = memory_context.get("total_investigations", 0)
            memory_summary = f"""
MEMORY CONTEXT:
- Total past investigations: {total}
- Recent investigations (last 7 days): {recent_count}
- Recurring unresolved issues: {recurring_count}
"""
            if memory_context.get("recent_investigations"):
                memory_summary += "\nRecent investigations:\n"
                for inv in memory_context["recent_investigations"]:
                    memory_summary += f"- {inv.get('timestamp', '')}: {inv.get('user_query', '')[:50]}...\n"

            if memory_context.get("recurring_issues"):
                memory_summary += "\nRecurring performance issues:\n"
                for issue in memory_context["recurring_issues"]:
                    memory_summary += (
                        f"- {issue.get('collection', '')}: "
                        f"{issue.get('query_pattern', '')[:30]}... "
                        f"(detected {issue.get('detection_count', 0)} times)\n"
                    )

        intent_prompt = f"""
You are a MongoDB DBA AI assistant with memory of past investigations. Analyze this user request and determine how to respond.

USER REQUEST: "{user_input}"
{memory_summary}

Consider these categories:
1. **DIRECT_ANSWER**: Questions that don't need database analysis (greetings, identity questions, general chat)
2. **DATABASE_METADATA**: Questions about database structure, collections, schemas
3. **PERFORMANCE_ANALYSIS**: Questions about slow queries, optimization, performance issues
4. **COMPLEX_INVESTIGATION**: Multi-step questions requiring several tools

Analyze the request and respond with JSON:
{{
    "intent_category": "DIRECT_ANSWER|DATABASE_METADATA|PERFORMANCE_ANALYSIS|COMPLEX_INVESTIGATION",
    "confidence": 0.0-1.0,
    "reasoning": "Why you chose this category",
    "requires_database": true/false,
    "suggested_response": "For DIRECT_ANSWER category, provide the response here",
    "tool_needed": "tool_name or null",
    "database_target": "database name if applicable"
}}

Examples:
- "what's your name" → DIRECT_ANSWER (no database needed)
- "how many collections" → DATABASE_METADATA (metadata tool needed)
- "database is slow" → PERFORMANCE_ANALYSIS (performance tools needed)
- "optimize my database" → COMPLEX_INVESTIGATION (multiple tools needed)
"""
        try:
            response = self.llm.invoke(intent_prompt)
            logger.info("Intent classification: %s", response)
            intent = json.loads(self.clean_llm_response(response))
            return {
                "category": intent.get("intent_category", "DATABASE_METADATA"),
                "confidence": intent.get("confidence", 0.5),
                "reasoning": intent.get("reasoning", ""),
                "requires_database": intent.get("requires_database", True),
                "suggested_response": intent.get("suggested_response", ""),
                "tool_needed": intent.get("tool_needed"),
                "database_target": "testdb",
            }
        except Exception as e:
            logger.error("Error in intent classification: %s", e)
            return {
                "category": "DATABASE_METADATA",
                "confidence": 0.3,
                "reasoning": f"Fallback due to classification error: {e}",
                "requires_database": True,
                "suggested_response": "",
                "tool_needed": "list_collections",
                "database_target": "testdb",
            }

    def select_tools_intelligently(
        self, user_input: str, intent: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        tool_descriptions = {
            name: tool["description"] + " | Use when: " + tool["use_when"]
            for name, tool in self.tools.items()
        }

        selection_prompt = f"""
You are planning an investigation for a MongoDB DBA task.

USER REQUEST: "{user_input}"
INTENT ANALYSIS: {json.dumps(intent, indent=2)}

AVAILABLE TOOLS:
{json.dumps(tool_descriptions, indent=2)}

Plan the investigation by choosing tools that will help answer the user's question.
Think about:
1. What information do you need?
2. What tools can provide that information?
3. What order makes logical sense?
4. When will you have enough information?

Respond with JSON:
{{
    "investigation_plan": [
        {{
            "step": 1,
            "tool": "tool_name",
            "reasoning": "why this tool first",
            "parameters": {{"database": "testdb"}},
            "expected_outcome": "what this will tell us"
        }}
    ],
    "estimated_steps": 1-3,
    "investigation_type": "simple|complex"
}}

Guidelines:
- For metadata questions: Usually 1 tool (list_collections, list_databases)
- For performance questions: Usually 2-3 tools (fetch_slow_queries → check_indexes → explain_query)
- Choose tools based on what the user actually asked, not rigid rules
"""
        try:
            response = self.llm.invoke(selection_prompt)
            logger.info("Tool selection: %s", response)
            plan = json.loads(self.clean_llm_response(response))
            return plan.get("investigation_plan", [])
        except Exception as e:
            logger.error("Error in tool selection: %s", e)
            if intent["category"] == "DATABASE_METADATA":
                return [{
                    "step": 1,
                    "tool": "list_collections",
                    "reasoning": "Fallback: provide database structure information",
                    "parameters": {"database": "testdb"},
                    "expected_outcome": "List of collections in database",
                }]
            elif intent["category"] in ("PERFORMANCE_ANALYSIS", "COMPLEX_INVESTIGATION"):
                return [{
                    "step": 1,
                    "tool": "fetch_slow_queries",
                    "reasoning": "Fallback: identify performance bottlenecks",
                    "parameters": {"database": "testdb"},
                    "expected_outcome": "List of slow queries",
                }]
            return []

    # ── MCP tool execution ─────────────────────────────────────────────────────

    def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info("Executing tool: %s with parameters: %s", tool_name, parameters)
        try:
            if tool_name == "list_collections":
                return self._tool_list_collections(parameters)
            elif tool_name == "list_databases":
                return self._tool_list_databases()
            elif tool_name == "fetch_slow_queries":
                return self._tool_fetch_slow_queries(parameters)
            elif tool_name == "explain_query":
                return self._tool_explain_query(parameters)
            elif tool_name == "check_indexes":
                return self._tool_check_indexes(parameters)
            else:
                return {"success": False, "tool": tool_name, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error("Error executing tool %s: %s", tool_name, e)
            return {"success": False, "tool": tool_name, "error": str(e)}

    def _tool_list_collections(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = params.get("database", "testdb")
        collections = self._mcp.list_collections(db)
        return {
            "success": True,
            "tool": "list_collections",
            "data": {"database": db, "collections": collections, "collection_count": len(collections)},
            "summary": f"Found {len(collections)} collections in '{db}'",
        }

    def _tool_list_databases(self) -> Dict[str, Any]:
        databases = self._mcp.list_databases()
        return {
            "success": True,
            "tool": "list_databases",
            "data": {"databases": databases, "database_count": len(databases)},
            "summary": f"Found {len(databases)} databases",
        }

    def _tool_fetch_slow_queries(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = params.get("database", "testdb")
        threshold_ms = params.get("threshold_ms", self.config.agent.slow_query_threshold_ms)
        limit = params.get("limit", self.config.agent.max_queries_to_analyze)

        docs = self._mcp.find(
            db, "system.profile",
            filter={"millis": {"$gte": threshold_ms}, "op": {"$nin": ["getmore", "killCursors"]}},
            sort={"ts": -1},
            limit=limit,
        )
        queries = []
        for doc in docs:
            ns = doc.get("ns", "")
            collection = ns.split(".", 1)[-1] if "." in ns else ns
            queries.append({
                "collection": collection,
                "query": doc.get("query", doc.get("command", {})),
                "execution_time_ms": doc.get("millis", 0),
                "docs_examined": doc.get("docsExamined", 0),
                "docs_returned": doc.get("nreturned", 0),
                "operation": doc.get("op", "query"),
            })

        return {
            "success": True,
            "tool": "fetch_slow_queries",
            "data": queries,
            "summary": f"Found {len(queries)} slow queries (threshold: {threshold_ms}ms)",
        }

    def _tool_explain_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = params.get("database", "testdb")
        collection = params.get("collection", "users")
        filter_query = params.get("filter", {})

        plan = self._mcp.explain(
            db, collection, [{"name": "find", "arguments": {"filter": filter_query}}]
        )
        return {
            "success": True,
            "tool": "explain_query",
            "data": plan,
            "summary": f"Execution plan retrieved for '{collection}'",
        }

    def _tool_check_indexes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        db = params.get("database", "testdb")
        collection = params.get("collection", "users")

        indexes = self._mcp.collection_indexes(db, collection)
        return {
            "success": True,
            "tool": "check_indexes",
            "data": {"collection": collection, "indexes": indexes, "index_count": len(indexes)},
            "summary": f"Found {len(indexes)} indexes on '{collection}'",
        }

    # ── memory helpers ─────────────────────────────────────────────────────────

    def _create_query_hash(self, query: Dict[str, Any], collection: str) -> str:
        query_str = json.dumps(query, sort_keys=True) + collection
        return hashlib.md5(query_str.encode()).hexdigest()

    def _store_investigation_memory(
        self,
        user_input: str,
        intent: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        investigation_time: float,
        final_response: str,
    ) -> None:
        try:
            investigation = Investigation(
                investigation_id=f"inv_{int(time.time())}",
                timestamp=datetime.utcnow(),
                user_query=user_input,
                intent_category=intent["category"],
                database_analyzed=intent.get("database_target", "testdb"),
                cluster_uri=self._cluster_uri,
                tools_used=[r.get("tool", "unknown") for r in tool_results],
                findings={
                    "tool_results": tool_results,
                    "final_response_summary": (
                        final_response[:200] + "..."
                        if len(final_response) > 200
                        else final_response
                    ),
                },
                recommendations=[],
                investigation_time_seconds=investigation_time,
            )

            recommendations = []
            performance_issues = []

            for result in tool_results:
                if result.get("tool") == "fetch_slow_queries" and result.get("success"):
                    for qdata in result.get("data", []):
                        qhash = self._create_query_hash(
                            qdata.get("query", {}), qdata.get("collection", "")
                        )
                        issue = PerformanceIssue(
                            issue_id=f"perf_{qhash}",
                            database=intent.get("database_target", "testdb"),
                            collection=qdata.get("collection", ""),
                            cluster_uri=self._cluster_uri,
                            query_pattern=str(qdata.get("query", {}))[:200],
                            query_hash=qhash,
                            first_detected=datetime.utcnow(),
                            last_detected=datetime.utcnow(),
                            detection_count=1,
                            avg_execution_time_ms=qdata.get("execution_time_ms", 0),
                            recommended_action=(
                                f"Analyze execution plan and consider indexing "
                                f"for {qdata.get('collection', 'collection')}"
                            ),
                            severity="medium",
                        )
                        performance_issues.append(issue)
                        recommendations.append({
                            "type": "performance",
                            "collection": qdata.get("collection"),
                            "action": f"Optimize query with {qdata.get('execution_time_ms', 0)}ms execution time",
                            "priority": "medium",
                        })

            investigation.recommendations = recommendations
            inv_id = self.memory.store_investigation(investigation)
            for issue in performance_issues:
                self.memory.store_performance_issue(issue)

            logger.info(
                "Stored investigation %s with %d performance issues",
                inv_id,
                len(performance_issues),
            )
        except Exception as e:
            logger.error("Error storing investigation memory: %s", e)

    # ── response generation ────────────────────────────────────────────────────

    def _generate_memory_aware_response(
        self,
        user_input: str,
        intent: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        memory_context: Dict[str, Any],
    ) -> str:
        if intent["category"] == "DIRECT_ANSWER":
            return intent.get(
                "suggested_response",
                "I'm a MongoDB DBA assistant. How can I help you with your database?",
            )

        memory_context_str = ""
        recurring_issues = memory_context.get("recurring_issues", [])
        if recurring_issues:
            memory_context_str += "\n🔄 RECURRING ISSUES DETECTED:\n"
            for issue in recurring_issues[:3]:
                memory_context_str += (
                    f"- {issue.get('collection', 'unknown')}: "
                    f"{issue.get('recommended_action', 'no action')} "
                    f"(detected {issue.get('detection_count', 0)} times, "
                    f"last: {str(issue.get('last_detected', ''))[:10]})\n"
                )

        recent = memory_context.get("recent_investigations", [])
        similar = [i for i in recent if i.get("intent_category") == intent["category"]]
        if similar:
            memory_context_str += "\n📋 RECENT SIMILAR INVESTIGATIONS:\n"
            for inv in similar[:2]:
                memory_context_str += (
                    f"- {str(inv.get('timestamp', ''))[:10]}: "
                    f"{inv.get('user_query', 'no query')[:40]}...\n"
                )

        synthesis_prompt = f"""
You are a MongoDB DBA assistant with memory of past investigations. Provide a response that incorporates historical context.

USER QUESTION: "{user_input}"
INTENT: {intent["reasoning"]}

CURRENT INVESTIGATION RESULTS:
{json.dumps(tool_results, indent=2)}

MEMORY CONTEXT:
{memory_context_str}

Guidelines:
- Reference relevant past investigations or recurring issues
- If this is a recurring issue, mention when it was last seen
- Provide specific recommendations based on both current and historical data
- Be helpful and contextual - use the memory to provide better insights

Format your response as conversational text that acknowledges the history while answering the current question.
"""
        try:
            response = self.llm.invoke(synthesis_prompt)
            logger.info("Generated memory-aware response")
            return response.strip()
        except Exception as e:
            logger.error("Error generating memory-aware response: %s", e)
            return self._generate_structured_fallback(user_input, tool_results, memory_context)

    def generate_final_response(
        self,
        user_input: str,
        intent: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        memory_context: Dict[str, Any] = None,
    ) -> str:
        return self._generate_memory_aware_response(
            user_input, intent, tool_results, memory_context or {}
        )

    def _generate_structured_fallback(
        self,
        user_input: str,
        tool_results: List[Dict[str, Any]],
        memory_context: Dict[str, Any],
    ) -> str:
        out = f"📋 RESPONSE TO: {user_input}\n\n"
        total = memory_context.get("total_investigations", 0)
        recurring = len(memory_context.get("recurring_issues", []))
        if total > 0:
            out += f"🧠 MEMORY: {total} past investigations"
            if recurring:
                out += f", {recurring} recurring issues"
            out += "\n\n"

        for result in tool_results:
            if result.get("success"):
                out += f"✅ {result['tool']}: {result.get('summary', 'Completed')}\n"
                data = result.get("data", {})
                if result["tool"] == "list_collections":
                    for c in data.get("collections", []):
                        name = c.get("name", c) if isinstance(c, dict) else c
                        out += f"  • {name}\n"
                elif result["tool"] == "fetch_slow_queries":
                    for q in data[:3]:
                        out += f"  • {q['collection']}: {q['execution_time_ms']}ms\n"
                elif result["tool"] == "check_indexes":
                    out += f"  • {data.get('index_count', 0)} indexes on '{data.get('collection', '')}'\n"
            else:
                out += f"❌ {result.get('tool', 'tool')}: {result.get('error', 'Unknown error')}\n"

        if memory_context.get("recurring_issues"):
            out += "\n🔄 RECURRING ISSUES:\n"
            for issue in memory_context["recurring_issues"][:2]:
                out += f"  • {issue.get('collection', 'unknown')}: seen {issue.get('detection_count', 0)} times\n"
        return out

    # ── main entry point ───────────────────────────────────────────────────────

    def investigate(self, user_input: str) -> str:
        logger.info("Starting memory-enabled investigation for: %s", user_input)
        start_time = time.time()

        try:
            # Step 1: memory context
            memory_context = self.memory.get_investigation_context(user_input, "testdb")
            logger.info(
                "Retrieved memory context: %d past investigations",
                memory_context.get("total_investigations", 0),
            )

            # Step 2: intent classification
            intent = self.classify_user_intent(user_input, memory_context)
            logger.info(
                "Intent classification: %s (confidence: %s)",
                intent["category"],
                intent["confidence"],
            )

            # Step 3: direct answers need no database
            if intent["category"] == "DIRECT_ANSWER":
                elapsed = time.time() - start_time
                response = intent.get(
                    "suggested_response",
                    "I'm a MongoDB DBA assistant focused on helping with database tasks.",
                )
                return f"{response}\n\n⏱️  Response time: {elapsed:.1f} seconds\n💬 Direct response (no database analysis needed)"

            if not intent["requires_database"]:
                elapsed = time.time() - start_time
                return (
                    "I don't think this question requires database analysis. "
                    "Could you clarify what specific database information you're looking for?\n\n"
                    f"⏱️  Response time: {elapsed:.1f} seconds"
                )

            # Step 4: tool selection
            investigation_plan = self.select_tools_intelligently(user_input, intent)
            logger.info("Investigation plan: %d steps", len(investigation_plan))

            if not investigation_plan:
                elapsed = time.time() - start_time
                return (
                    "I'm not sure how to help with that question. "
                    "Could you be more specific about what database information you need?\n\n"
                    f"⏱️  Response time: {elapsed:.1f} seconds"
                )

            # Step 5: execute via MCP (one subprocess for entire investigation)
            tool_results = []
            with MCPClient(self._mcp_uri) as mcp:
                self._mcp = mcp
                for step in investigation_plan:
                    tool_name = step.get("tool")
                    parameters = step.get("parameters", {})
                    reasoning = step.get("reasoning", "")
                    logger.info(
                        "Step %d: %s — %s", step.get("step", 1), tool_name, reasoning
                    )
                    result = self.execute_tool(tool_name, parameters)
                    tool_results.append(result)

                    # Short-circuit for simple metadata questions
                    if (
                        len(tool_results) == 1
                        and intent["category"] == "DATABASE_METADATA"
                        and result.get("success")
                    ):
                        break
                self._mcp = None

            # Step 6: synthesise response with memory
            final_response = self.generate_final_response(
                user_input, intent, tool_results, memory_context
            )
            elapsed = time.time() - start_time

            # Step 7: persist investigation
            self._store_investigation_memory(
                user_input, intent, tool_results, elapsed, final_response
            )

            memory_stats = f"🧠 Memory-enhanced investigation with {len(tool_results)} analysis step(s)"
            if memory_context.get("total_investigations", 0) > 0:
                memory_stats += f" (building on {memory_context['total_investigations']} past investigations)"

            return f"{final_response}\n\n⏱️  Investigation time: {elapsed:.1f} seconds\n{memory_stats}"

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("Investigation failed: %s", e)
            return (
                f"I encountered an error while investigating your question: {e}\n\n"
                f"⏱️  Time: {elapsed:.1f} seconds\n"
                "❌ Please try rephrasing your question."
            )

    def get_memory_stats(self) -> Dict[str, Any]:
        return self.memory.get_memory_stats()

    def close(self) -> None:
        try:
            self.memory.close()
            logger.info("Agent resources cleaned up")
        except Exception as e:
            logger.error("Error during cleanup: %s", e)
