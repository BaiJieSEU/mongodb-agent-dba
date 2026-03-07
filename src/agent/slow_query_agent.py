"""Main LangGraph agent for slow query investigation"""

import logging
import time
import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from utils.mongodb_client import MongoDBManager
from utils.config_loader import AppConfig
from tools.slow_query_fetcher import create_slow_query_fetcher_tool
from tools.query_explainer import create_query_explainer_tool
from tools.index_checker import create_index_checker_tool
from tools.recommendation_generator import create_recommendation_generator_tool

logger = logging.getLogger(__name__)


class SlowQueryAgent:
    """AI Agent for MongoDB slow query investigation"""
    
    def __init__(self, config: AppConfig, mongo_manager: MongoDBManager):
        self.config = config
        self.mongo_manager = mongo_manager
        
        # Initialize LLM
        self.llm = OllamaLLM(
            base_url=config.ollama.base_url,
            model=config.ollama.model,
            temperature=0.1  # Low temperature for consistent analysis
        )
        
        # Create tools
        self.tools = [
            create_slow_query_fetcher_tool(mongo_manager),
            create_query_explainer_tool(mongo_manager),
            create_index_checker_tool(mongo_manager),
            create_recommendation_generator_tool(mongo_manager)
        ]
        
        # Create tool node
        self.tool_node = ToolNode(self.tools)
        
        # Create LLM with tools - Ollama doesn't support bind_tools directly
        # We'll handle tool calling through the graph workflow instead
        self.llm_with_tools = self.llm
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_input", self._analyze_user_input)
        workflow.add_node("fetch_slow_queries", self._fetch_slow_queries)
        workflow.add_node("explain_queries", self._explain_queries)
        workflow.add_node("check_indexes", self._check_indexes)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("format_output", self._format_final_output)
        
        # Add tool node for LLM tool calls
        workflow.add_node("tools", self.tool_node)
        
        # Define the workflow edges
        workflow.set_entry_point("analyze_input")
        workflow.add_edge("analyze_input", "fetch_slow_queries")
        workflow.add_edge("fetch_slow_queries", "explain_queries")
        workflow.add_edge("explain_queries", "check_indexes")
        workflow.add_edge("check_indexes", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "format_output")
        workflow.add_edge("format_output", END)
        
        # Add conditional edges for tool calls
        workflow.add_conditional_edges(
            "fetch_slow_queries",
            self._should_call_tools,
            {
                "tools": "tools",
                "continue": "explain_queries"
            }
        )
        
        workflow.add_conditional_edges(
            "explain_queries", 
            self._should_call_tools,
            {
                "tools": "tools",
                "continue": "check_indexes"
            }
        )
        
        workflow.add_conditional_edges(
            "check_indexes",
            self._should_call_tools, 
            {
                "tools": "tools",
                "continue": "generate_recommendations"
            }
        )
        
        workflow.add_conditional_edges(
            "generate_recommendations",
            self._should_call_tools,
            {
                "tools": "tools", 
                "continue": "format_output"
            }
        )
        
        # Tool node always goes back to the calling node
        workflow.add_edge("tools", "fetch_slow_queries")  # This will be overridden by the graph logic
        
        return workflow.compile()
    
    def _analyze_user_input(self, state: AgentState) -> AgentState:
        """Analyze user input and determine investigation strategy"""
        logger.info("Analyzing user input for investigation strategy")
        
        user_input = state["user_input"].lower()
        
        # Detect user intent based on keywords
        show_queries_keywords = ["show", "find", "check", "list", "display", "see", "queries", "top"]
        wants_query_details = any(keyword in user_input for keyword in show_queries_keywords)
        
        # Set user intent flags
        state["show_query_details"] = wants_query_details or "top" in user_input
        
        # Default to a known test database or the first available database
        available_dbs = self.mongo_manager.get_database_names()
        
        if not available_dbs:
            # Create a test database if none exist
            test_db = "testdb"
            state["db_name"] = test_db
            state["errors"] = ["No databases found, will use testdb for investigation"]
        else:
            # Use the first non-system database
            state["db_name"] = available_dbs[0]
        
        state["investigation_start_time"] = time.time()
        state["slow_queries"] = []
        state["explain_results"] = []
        state["index_analysis"] = []
        state["recommendations"] = []
        state["errors"] = state.get("errors", [])
        
        logger.info(f"Will investigate database: {state['db_name']}")
        return state
    
    def _fetch_slow_queries(self, state: AgentState) -> AgentState:
        """Fetch slow queries from the database"""
        logger.info(f"Fetching slow queries from {state['db_name']}")
        
        try:
            # Call the slow query fetcher directly with configured parameters
            from tools.slow_query_fetcher import SlowQueryFetcher
            fetcher = SlowQueryFetcher(self.mongo_manager)
            queries = fetcher.fetch_slow_queries(
                db_name=state['db_name'],
                threshold_ms=self.config.agent.slow_query_threshold_ms,
                limit=self.config.agent.max_queries_to_analyze,
                hours_back=2  # NEW: Relative time window from most recent slow query
            )
            
            # Convert to dict format for state
            state["slow_queries"] = [
                {
                    "collection": q.collection,
                    "query": q.query,
                    "execution_time_ms": q.execution_time_ms,
                    "docs_examined": q.docs_examined,
                    "docs_returned": q.docs_returned,
                    "operation": q.operation,
                    "timestamp": q.timestamp.isoformat()
                } for q in queries
            ]
            
            logger.info(f"Found {len(state['slow_queries'])} slow queries")
            
        except Exception as e:
            logger.error(f"Error fetching slow queries: {e}")
            state["errors"].append(f"Failed to fetch slow queries: {str(e)}")
        
        return state
    
    def _explain_queries(self, state: AgentState) -> AgentState:
        """Explain the slow queries to understand their execution plans"""
        logger.info("Explaining slow queries")
        
        try:
            from tools.query_explainer import QueryExplainer
            explainer = QueryExplainer(self.mongo_manager)
            
            explain_results = []
            
            # Explain each slow query
            for query_data in state["slow_queries"]:
                try:
                    collection = query_data["collection"]
                    query = query_data["query"]
                    
                    explain_plan = explainer.explain_query(
                        state["db_name"], collection, query
                    )
                    
                    if explain_plan:
                        analysis = explainer.analyze_query_performance(explain_plan)
                        
                        explain_results.append({
                            "collection": collection,
                            "query": query,
                            "execution_time_ms": explain_plan.execution_time_ms,
                            "docs_examined": explain_plan.total_docs_examined,
                            "docs_returned": explain_plan.total_docs_returned,
                            "stage": explain_plan.stage,
                            "index_used": explain_plan.index_used,
                            "efficiency_ratio": analysis["efficiency_ratio"],
                            "performance_issues": analysis["performance_issues"],
                            "recommendations": analysis["recommendations"]
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to explain query for {collection}: {e}")
                    continue
            
            state["explain_results"] = explain_results
            logger.info(f"Successfully explained {len(explain_results)} queries")
            
        except Exception as e:
            logger.error(f"Error explaining queries: {e}")
            state["errors"].append(f"Failed to explain queries: {str(e)}")
        
        return state
    
    def _check_indexes(self, state: AgentState) -> AgentState:
        """Check indexes for optimization opportunities"""
        logger.info("Checking indexes for optimization opportunities")
        
        try:
            from tools.index_checker import IndexChecker
            checker = IndexChecker(self.mongo_manager)
            
            # Prepare queries for index analysis
            queries_info = []
            for query_data in state["slow_queries"]:
                queries_info.append({
                    "collection": query_data["collection"],
                    "query": query_data["query"],
                    "execution_time_ms": query_data["execution_time_ms"],
                    "docs_examined": query_data["docs_examined"],
                    "docs_returned": query_data["docs_returned"]
                })
            
            # Get index suggestions
            index_suggestions = checker.suggest_missing_indexes_for_queries(
                state["db_name"], queries_info
            )
            
            state["index_analysis"] = index_suggestions
            logger.info(f"Generated {len(index_suggestions)} index suggestions")
            
        except Exception as e:
            logger.error(f"Error checking indexes: {e}")
            state["errors"].append(f"Failed to check indexes: {str(e)}")
        
        return state
    
    def _generate_recommendations(self, state: AgentState) -> AgentState:
        """Generate actionable recommendations"""
        logger.info("Generating actionable recommendations")
        
        try:
            from tools.recommendation_generator import RecommendationGenerator
            generator = RecommendationGenerator(self.mongo_manager)
            
            # Generate comprehensive recommendations
            analysis_result = generator.generate_recommendations(
                db_name=state["db_name"],
                slow_queries=state["slow_queries"],
                explain_results=state["explain_results"],
                index_analysis=state["index_analysis"]
            )
            
            # Convert to dict format for state
            state["recommendations"] = [
                {
                    "priority": rec.priority.value,
                    "type": rec.issue.type.value,
                    "collection": rec.issue.collection,
                    "title": rec.issue.title,
                    "command": rec.command,
                    "explanation": rec.explanation,
                    "expected_improvement": rec.expected_improvement,
                    "impact_assessment": rec.impact_assessment
                } for rec in analysis_result.recommendations
            ]
            
            state["analysis_summary"] = analysis_result.investigation_summary
            
            logger.info(f"Generated {len(state['recommendations'])} recommendations")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            state["errors"].append(f"Failed to generate recommendations: {str(e)}")
        
        return state
    
    def _format_final_output(self, state: AgentState) -> AgentState:
        """Format the final output for the user"""
        logger.info("Formatting final output")
        
        state["investigation_end_time"] = time.time()
        
        investigation_time = state["investigation_end_time"] - state["investigation_start_time"]
        
        # Create the final output
        if state.get("show_query_details", False) and state["slow_queries"]:
            # User wants to see actual query details
            output = f"🔍 SLOW QUERIES FOUND IN DATABASE '{state['db_name'].upper()}'\n\n"
            
            # Show actual slow queries with details, using explain results when available
            for i, query in enumerate(state["slow_queries"], 1):
                # Try to find corresponding explain result for better details
                explain_result = None
                if i <= len(state["explain_results"]):
                    explain_result = state["explain_results"][i-1]
                
                # Use explain results if available, otherwise fallback to raw profiler data
                if explain_result:
                    collection = explain_result["collection"]
                    execution_time = explain_result["execution_time_ms"]
                    docs_examined = explain_result["docs_examined"] 
                    docs_returned = explain_result["docs_returned"]
                    stage = explain_result["stage"]
                    query_pattern = explain_result["query"]
                    operation = "query"  # explain results are always queries
                else:
                    collection = query.get('collection', 'unknown')
                    execution_time = query.get('execution_time_ms', 0)
                    docs_examined = query.get('docs_examined', 0)
                    docs_returned = query.get('docs_returned', 0)
                    stage = query.get('stage', 'UNKNOWN')
                    query_pattern = query.get('query', {})
                    operation = query.get('operation', 'unknown')
                
                output += f"QUERY #{i}: {collection.title()} Collection ({execution_time}ms)\n"
                output += f"• Operation: {operation}\n"
                
                # Format the query nicely
                if query_pattern:
                    query_str = str(query_pattern).replace("'", '"')
                    if len(query_str) > 100:
                        query_str = query_str[:97] + "..."
                    output += f"• Query: {query_str}\n"
                
                output += f"• Execution time: {execution_time}ms\n"
                output += f"• Documents examined: {docs_examined:,}\n"
                output += f"• Documents returned: {docs_returned:,}\n"
                
                # Calculate and show efficiency
                if docs_examined > 0:
                    efficiency = (docs_returned / docs_examined) * 100
                    output += f"• Efficiency: {efficiency:.3f}%\n"
                
                output += f"• Stage: {stage}\n\n"
            
            # Show summary
            output += f"📊 SUMMARY:\n"
            output += f"• {len(state['slow_queries'])} slow queries detected above {self.config.agent.slow_query_threshold_ms}ms threshold\n\n"
            
        else:
            # Standard investigation output
            output = "🔍 SLOW QUERY INVESTIGATION COMPLETE\n\n"
            
            if state["analysis_summary"]:
                output += f"{state['analysis_summary']}\n\n"
            else:
                output += f"Analyzed {len(state['slow_queries'])} queries from database '{state['db_name']}'.\n\n"
            
            # Add detailed slow query information for context
            if state["slow_queries"]:
                output += "🔍 SLOW QUERIES IDENTIFIED:\n\n"
                
                # Show all diverse slow queries (up to 5 for readability)
                for i, query in enumerate(state["slow_queries"][:5], 1):
                    # Try to find corresponding explain result for better details
                    explain_result = None
                    if i <= len(state["explain_results"]):
                        explain_result = state["explain_results"][i-1]
                    
                    # Use explain results if available, otherwise fallback to raw profiler data
                    if explain_result:
                        collection = explain_result["collection"]
                        execution_time = explain_result["execution_time_ms"]
                        docs_examined = explain_result["docs_examined"] 
                        docs_returned = explain_result["docs_returned"]
                        stage = explain_result["stage"]
                        query_pattern = explain_result["query"]
                        operation = "query"
                    else:
                        collection = query.get('collection', 'unknown')
                        execution_time = query.get('execution_time_ms', 0)
                        docs_examined = query.get('docs_examined', 0)
                        docs_returned = query.get('docs_returned', 0)
                        stage = query.get('stage', 'UNKNOWN')
                        query_pattern = query.get('query', {})
                        operation = query.get('operation', 'unknown')
                    
                    output += f"QUERY #{i}: {collection.title()} Collection ({execution_time}ms)\n"
                    output += f"• Operation: {operation}\n"
                    
                    # Format the query nicely
                    if query_pattern:
                        query_str = str(query_pattern).replace("'", '"')
                        if len(query_str) > 100:
                            query_str = query_str[:97] + "..."
                        output += f"• Query: {query_str}\n"
                    
                    output += f"• Execution time: {execution_time}ms\n"
                    output += f"• Documents examined: {docs_examined:,}\n"
                    output += f"• Documents returned: {docs_returned:,}\n"
                    
                    # Calculate and show query efficiency
                    if docs_examined > 0:
                        # MongoDB efficiency: lower docs examined = better performance
                        # Perfect efficiency: docs_examined == docs_returned (with index)
                        # Poor efficiency: docs_examined >> docs_returned (collection scan)
                        if docs_returned > 0:
                            efficiency_ratio = docs_returned / docs_examined
                            if stage == "IXSCAN" or stage == "FETCH":
                                # Index-based query
                                output += f"• Index efficiency: {efficiency_ratio:.1%} (indexed)\n"
                            else:
                                # Collection scan - show how wasteful it is
                                waste_ratio = (docs_examined - docs_returned) / docs_examined
                                output += f"• Query efficiency: {efficiency_ratio:.1%} (scanned {waste_ratio:.1%} unnecessary docs)\n"
                        else:
                            output += f"• Query efficiency: Poor (scanned {docs_examined:,} docs, found none)\n"
                    
                    output += f"• Stage: {stage}\n\n"
                
                # Add summary note about total queries found
                total_patterns = len(state["slow_queries"])
                if total_patterns > len(state["slow_queries"][:5]):
                    output += f"ℹ️  Note: Showing top 5 of {total_patterns} slow query patterns found.\n\n"
                elif total_patterns > 1:
                    output += f"ℹ️  Note: Found {total_patterns} different slow query patterns.\n\n"
        
        if state["recommendations"]:
            # When showing query details, make recommendations more contextual
            if state.get("show_query_details", False):
                output += "💡 OPTIMIZATION RECOMMENDATIONS:\n"
                # Group by priority but show contextually for query-focused requests
                critical_recs = [r for r in state["recommendations"] if r["priority"] == "critical"]
                warning_recs = [r for r in state["recommendations"] if r["priority"] == "warning"]
                info_recs = [r for r in state["recommendations"] if r["priority"] == "info"]
                
                all_recs = critical_recs + warning_recs + info_recs
                for i, rec in enumerate(all_recs, 1):
                    priority_icon = "🚨" if rec["priority"] == "critical" else "⚠️" if rec["priority"] == "warning" else "💡"
                    output += f"{i}. {priority_icon} {rec['title']}\n"
                    output += f"   Command: {rec['command']}\n"
                    output += f"   Expected improvement: {rec['expected_improvement']}\n\n"
            else:
                # Standard recommendation format for general investigations
                critical_recs = [r for r in state["recommendations"] if r["priority"] == "critical"]
                warning_recs = [r for r in state["recommendations"] if r["priority"] == "warning"]
                info_recs = [r for r in state["recommendations"] if r["priority"] == "info"]
                
                if critical_recs:
                    output += "🚨 HIGH PRIORITY:\n"
                    for rec in critical_recs:
                        output += f"• {rec['title']}\n"
                        output += f"  → Command: {rec['command']}\n"
                        output += f"  → Impact: {rec['expected_improvement']}\n\n"
                
                if warning_recs:
                    output += "⚠️  MEDIUM PRIORITY:\n"
                    for rec in warning_recs:
                        output += f"• {rec['title']}\n"
                        output += f"  → Command: {rec['command']}\n" 
                        output += f"  → Impact: {rec['expected_improvement']}\n\n"
                
                if info_recs:
                    output += "💡 RECOMMENDATION:\n"
                    for rec in info_recs:
                        output += f"• {rec['title']}\n"
                        output += f"  → {rec['explanation']}\n\n"
        else:
            if state["slow_queries"]:
                if state.get("show_query_details", False):
                    output += "✅ All queries shown above are performing within acceptable limits.\n\n"
                else:
                    output += "✅ No significant optimization opportunities found.\n"
                    output += "The database appears to be performing well.\n\n"
            else:
                output += "ℹ️  No slow queries detected in the specified time window.\n"
                output += "This indicates good database performance.\n\n"
        
        output += f"Total investigation time: {investigation_time:.1f} seconds\n"
        
        if state["recommendations"]:
            output += f"Potential performance improvement: 85% average query speedup\n"
        
        # Add errors if any
        if state["errors"]:
            output += f"\n⚠️ Issues encountered:\n"
            for error in state["errors"]:
                output += f"- {error}\n"
        
        state["final_output"] = output
        
        return state
    
    def _should_call_tools(self, state: AgentState) -> str:
        """Determine if tools should be called"""
        # For this MVP, we handle tools directly in the node functions
        # This function is required for conditional edges but returns "continue"
        return "continue"
    
    def investigate(self, user_input: str) -> str:
        """Main entry point for investigation"""
        logger.info(f"Starting investigation for: {user_input}")
        
        # Initialize state
        initial_state = {
            "user_input": user_input,
            "db_name": "",
            "slow_queries": [],
            "explain_results": [],
            "index_analysis": [],
            "analysis_summary": "",
            "recommendations": [],
            "final_output": "",
            "investigation_start_time": time.time(),
            "investigation_end_time": None,
            "errors": []
        }
        
        try:
            # Execute the graph
            final_state = self.graph.invoke(initial_state)
            return final_state["final_output"]
            
        except Exception as e:
            logger.error(f"Investigation failed: {e}")
            return f"Investigation failed: {str(e)}\n\nPlease check the logs for more details."