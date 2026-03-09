"""Intelligent Agentic MongoDB DBA Agent with semantic understanding"""

import logging
import time
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_ollama import OllamaLLM

from utils.mongodb_client import MongoDBManager
from utils.config_loader import AppConfig
from tools.slow_query_fetcher import SlowQueryFetcher
from tools.query_explainer import QueryExplainer
from tools.index_checker import IndexChecker
from tools.metadata_inspector import MetadataInspector
from memory.agent_memory import AgentMemory, Investigation, PerformanceIssue

logger = logging.getLogger(__name__)


class IntelligentAgenticDBAAgent:
    """Intelligent AI Agent with semantic understanding and natural tool selection"""
    
    def __init__(self, config: AppConfig, mongo_manager: MongoDBManager):
        self.config = config
        self.mongo_manager = mongo_manager
        
        # Initialize LLM
        self.llm = OllamaLLM(
            base_url=config.ollama.base_url,
            model=config.ollama.model,
            temperature=0.1
        )
        
        # Initialize memory system
        self.memory = AgentMemory(
            connection_string=config.mongodb.agent_store,
            database_name="agent_memory"
        )
        
        # Initialize tools
        self.tools = {
            "list_collections": {
                "handler": MetadataInspector(mongo_manager),
                "method": "get_collections_info",
                "description": "Shows what collections exist in a database with document counts and sizes",
                "use_when": "User wants to know about database structure, available collections, or collection metadata",
                "example_queries": ["what collections do I have", "show me my tables", "how many collections"]
            },
            "list_databases": {
                "handler": MetadataInspector(mongo_manager),
                "method": "get_database_info", 
                "description": "Shows available databases with basic statistics",
                "use_when": "User wants to know what databases are available or database-level information",
                "example_queries": ["what databases exist", "show me available databases"]
            },
            "fetch_slow_queries": {
                "handler": SlowQueryFetcher(mongo_manager),
                "method": "fetch_slow_queries",
                "description": "Identifies queries that are performing poorly or taking too long",
                "use_when": "User reports performance problems, slowness, or wants optimization",
                "example_queries": ["database is slow", "find bottlenecks", "performance issues"]
            },
            "explain_query": {
                "handler": QueryExplainer(mongo_manager),
                "method": "explain_query",
                "description": "Analyzes specific query execution plans to understand performance",
                "use_when": "Need to understand why specific queries are slow",
                "example_queries": ["why is this query slow", "analyze query performance"]
            },
            "check_indexes": {
                "handler": IndexChecker(mongo_manager),
                "method": "suggest_missing_indexes_for_queries",
                "description": "Reviews index optimization opportunities for queries",
                "use_when": "Need to suggest index improvements for better performance",
                "example_queries": ["optimize indexes", "suggest database improvements"]
            }
        }
    
    def clean_llm_response(self, response: str) -> str:
        """Clean LLM response by removing markdown code blocks"""
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()
    
    def classify_user_intent(self, user_input: str, memory_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Use LLM to understand user intent and determine appropriate response"""
        
        # Include memory context in the prompt
        memory_summary = ""
        if memory_context:
            recent_count = len(memory_context.get("recent_investigations", []))
            recurring_count = len(memory_context.get("recurring_issues", []))
            total_investigations = memory_context.get("total_investigations", 0)
            
            memory_summary = f"""
MEMORY CONTEXT:
- Total past investigations: {total_investigations}
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
                    memory_summary += f"- {issue.get('collection', '')}: {issue.get('query_pattern', '')[:30]}... (detected {issue.get('detection_count', 0)} times)\n"

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
            logger.info(f"Intent classification: {response}")
            
            clean_response = self.clean_llm_response(response)
            intent = json.loads(clean_response)
            
            return {
                "category": intent.get("intent_category", "DATABASE_METADATA"),
                "confidence": intent.get("confidence", 0.5),
                "reasoning": intent.get("reasoning", ""),
                "requires_database": intent.get("requires_database", True),
                "suggested_response": intent.get("suggested_response", ""),
                "tool_needed": intent.get("tool_needed"),
                "database_target": "testdb"  # Default to testdb
            }
            
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            # Safe fallback
            return {
                "category": "DATABASE_METADATA",
                "confidence": 0.3,
                "reasoning": f"Fallback due to classification error: {str(e)}",
                "requires_database": True,
                "suggested_response": "",
                "tool_needed": "list_collections",
                "database_target": "testdb"
            }
    
    def select_tools_intelligently(self, user_input: str, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use LLM to intelligently select and sequence tools based on semantic understanding"""
        
        tool_descriptions = {name: tool["description"] + " | Use when: " + tool["use_when"] 
                           for name, tool in self.tools.items()}
        
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
- For performance questions: Usually 3-4 tools (fetch_slow_queries → explain_query → check_indexes)
- Choose tools based on what the user actually asked, not rigid rules
"""

        try:
            response = self.llm.invoke(selection_prompt)
            logger.info(f"Tool selection: {response}")
            
            clean_response = self.clean_llm_response(response)
            plan = json.loads(clean_response)
            
            return plan.get("investigation_plan", [])
            
        except Exception as e:
            logger.error(f"Error in tool selection: {e}")
            # Intelligent fallback based on intent
            if intent["category"] == "DATABASE_METADATA":
                return [{
                    "step": 1,
                    "tool": "list_collections",
                    "reasoning": "Fallback: provide database structure information",
                    "parameters": {"database": "testdb"},
                    "expected_outcome": "List of collections in database"
                }]
            elif intent["category"] == "PERFORMANCE_ANALYSIS":
                return [{
                    "step": 1,
                    "tool": "fetch_slow_queries", 
                    "reasoning": "Fallback: identify performance bottlenecks",
                    "parameters": {"database": "testdb"},
                    "expected_outcome": "List of slow queries"
                }]
            else:
                return []
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with given parameters"""
        logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
        
        try:
            if tool_name not in self.tools:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
            
            tool_info = self.tools[tool_name]
            handler = tool_info["handler"]
            method_name = tool_info["method"]
            
            if tool_name == "list_collections":
                result = handler.get_collections_info(parameters.get("database", "testdb"))
                return {
                    "success": True,
                    "tool": tool_name,
                    "data": result,
                    "summary": f"Found {result.get('collection_count', 0)} collections"
                }
                
            elif tool_name == "list_databases":
                result = handler.get_database_info()
                return {
                    "success": True,
                    "tool": tool_name,
                    "data": result,
                    "summary": f"Found {result.get('database_count', 0)} databases"
                }
                
            elif tool_name == "fetch_slow_queries":
                queries = handler.fetch_slow_queries(
                    db_name=parameters.get("database", "testdb"),
                    threshold_ms=parameters.get("threshold_ms", 5),
                    limit=parameters.get("limit", 10),
                    hours_back=parameters.get("hours_back", 2)
                )
                return {
                    "success": True,
                    "tool": tool_name,
                    "data": [
                        {
                            "collection": q.collection,
                            "query": q.query,
                            "execution_time_ms": q.execution_time_ms,
                            "docs_examined": q.docs_examined,
                            "docs_returned": q.docs_returned,
                            "operation": q.operation
                        } for q in queries
                    ],
                    "summary": f"Found {len(queries)} slow queries"
                }
                
            else:
                return {"success": False, "error": f"Tool execution not implemented: {tool_name}"}
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_query_hash(self, query: Dict[str, Any], collection: str) -> str:
        """Create a hash for query pattern to identify recurring issues"""
        query_str = json.dumps(query, sort_keys=True) + collection
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _store_investigation_memory(self, user_input: str, intent: Dict[str, Any], 
                                  tool_results: List[Dict[str, Any]], 
                                  investigation_time: float, final_response: str):
        """Store the investigation in memory for future reference"""
        try:
            # Create investigation record
            investigation = Investigation(
                investigation_id=f"inv_{int(time.time())}",
                timestamp=datetime.utcnow(),
                user_query=user_input,
                intent_category=intent["category"],
                database_analyzed=intent.get("database_target", "testdb"),
                tools_used=[result.get("tool", "unknown") for result in tool_results],
                findings={
                    "tool_results": tool_results,
                    "final_response_summary": final_response[:200] + "..." if len(final_response) > 200 else final_response
                },
                recommendations=[],  # Will be populated if performance analysis
                investigation_time_seconds=investigation_time
            )
            
            # Extract recommendations from tool results
            recommendations = []
            performance_issues = []
            
            for result in tool_results:
                if result.get("tool") == "fetch_slow_queries" and result.get("success"):
                    # Store performance issues for each slow query
                    slow_queries = result.get("data", [])
                    for query_data in slow_queries:
                        query_hash = self._create_query_hash(
                            query_data.get("query", {}), 
                            query_data.get("collection", "")
                        )
                        
                        issue = PerformanceIssue(
                            issue_id=f"perf_{query_hash}",
                            database=intent.get("database_target", "testdb"),
                            collection=query_data.get("collection", ""),
                            query_pattern=str(query_data.get("query", {}))[:200],
                            query_hash=query_hash,
                            first_detected=datetime.utcnow(),
                            last_detected=datetime.utcnow(),
                            detection_count=1,
                            avg_execution_time_ms=query_data.get("execution_time_ms", 0),
                            recommended_action=f"Analyze execution plan and consider indexing for {query_data.get('collection', 'collection')}",
                            severity="medium"
                        )
                        performance_issues.append(issue)
                        
                        recommendations.append({
                            "type": "performance",
                            "collection": query_data.get("collection"),
                            "action": f"Optimize query with {query_data.get('execution_time_ms', 0)}ms execution time",
                            "priority": "medium"
                        })
            
            investigation.recommendations = recommendations
            
            # Store in memory
            inv_id = self.memory.store_investigation(investigation)
            
            # Store performance issues
            for issue in performance_issues:
                self.memory.store_performance_issue(issue)
                
            logger.info(f"Stored investigation {inv_id} with {len(performance_issues)} performance issues")
            
        except Exception as e:
            logger.error(f"Error storing investigation memory: {e}")
    
    def _generate_memory_aware_response(self, user_input: str, intent: Dict[str, Any],
                                      tool_results: List[Dict[str, Any]], 
                                      memory_context: Dict[str, Any]) -> str:
        """Generate response that incorporates memory context"""
        
        if intent["category"] == "DIRECT_ANSWER":
            return intent.get("suggested_response", 
                             "I'm a MongoDB DBA assistant. How can I help you with your database?")
        
        # Build memory-aware context for LLM
        memory_context_str = ""
        
        # Check for recurring issues
        recurring_issues = memory_context.get("recurring_issues", [])
        if recurring_issues:
            memory_context_str += "\n🔄 RECURRING ISSUES DETECTED:\n"
            for issue in recurring_issues[:3]:  # Top 3
                memory_context_str += f"- {issue.get('collection', 'unknown')}: {issue.get('recommended_action', 'no action')} "
                memory_context_str += f"(detected {issue.get('detection_count', 0)} times, last: {str(issue.get('last_detected', ''))[:10]})\n"
        
        # Check for recent similar investigations
        recent_investigations = memory_context.get("recent_investigations", [])
        similar_recent = [inv for inv in recent_investigations 
                         if inv.get("intent_category") == intent["category"]]
        
        if similar_recent:
            memory_context_str += f"\n📋 RECENT SIMILAR INVESTIGATIONS:\n"
            for inv in similar_recent[:2]:  # Top 2
                memory_context_str += f"- {str(inv.get('timestamp', ''))[:10]}: {inv.get('user_query', 'no query')[:40]}...\n"
        
        # For database-related questions, use enhanced LLM synthesis
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
- If recommendations were given before but not implemented, mention that
- Be helpful and contextual - use the memory to provide better insights

Format your response as conversational text that acknowledges the history while answering the current question.
"""

        try:
            response = self.llm.invoke(synthesis_prompt)
            logger.info("Generated memory-aware response")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating memory-aware response: {e}")
            # Fallback to structured output with memory context
            return self._generate_structured_fallback_with_memory(user_input, tool_results, memory_context)
    
    def _generate_structured_fallback_with_memory(self, user_input: str, 
                                                tool_results: List[Dict[str, Any]], 
                                                memory_context: Dict[str, Any]) -> str:
        """Generate a structured fallback response that includes memory context"""
        output = f"📋 RESPONSE TO: {user_input}\n\n"
        
        # Add memory context
        recurring_count = len(memory_context.get("recurring_issues", []))
        total_investigations = memory_context.get("total_investigations", 0)
        
        if total_investigations > 0:
            output += f"🧠 MEMORY CONTEXT: {total_investigations} past investigations"
            if recurring_count > 0:
                output += f", {recurring_count} recurring unresolved issues"
            output += "\n\n"
        
        # Add current results
        for result in tool_results:
            if result.get("success"):
                tool_name = result.get("tool", "unknown")
                summary = result.get("summary", "Completed")
                output += f"✅ {tool_name}: {summary}\n"
                
                # Add specific details based on tool type
                data = result.get("data", {})
                if tool_name == "list_collections" and data.get("collections"):
                    output += f"\nCollections in {data.get('database', 'database')}:\n"
                    for coll in data["collections"]:
                        if "error" not in coll:
                            output += f"• {coll['name']}: {coll['count']:,} documents\n"
                            
                elif tool_name == "fetch_slow_queries" and data:
                    output += f"\nSlow queries found:\n"
                    for i, query in enumerate(data[:3], 1):
                        output += f"{i}. {query['collection']}: {query['execution_time_ms']}ms\n"
                        
            else:
                error = result.get("error", "Unknown error")
                output += f"❌ {result.get('tool', 'tool')}: {error}\n"
        
        # Add memory insights
        if memory_context.get("recurring_issues"):
            output += f"\n🔄 RECURRING ISSUES:\n"
            for issue in memory_context["recurring_issues"][:2]:
                output += f"• {issue.get('collection', 'unknown')}: seen {issue.get('detection_count', 0)} times\n"
        
        return output
    
    def generate_final_response(self, user_input: str, intent: Dict[str, Any], 
                              tool_results: List[Dict[str, Any]], 
                              memory_context: Dict[str, Any] = None) -> str:
        """Generate final response using LLM with investigation results and memory"""
        
        if memory_context:
            return self._generate_memory_aware_response(user_input, intent, tool_results, memory_context)
        else:
            return self._generate_legacy_response(user_input, intent, tool_results)
    
    def _generate_legacy_response(self, user_input: str, intent: Dict[str, Any], 
                                tool_results: List[Dict[str, Any]]) -> str:
        """Generate response without memory (fallback)"""
        
        if intent["category"] == "DIRECT_ANSWER":
            return intent.get("suggested_response", 
                             "I'm a MongoDB DBA assistant. How can I help you with your database?")
        
        synthesis_prompt = f"""
You are a MongoDB DBA assistant providing a final response to the user.

USER QUESTION: "{user_input}"
INTENT: {intent["reasoning"]}

INVESTIGATION RESULTS:
{json.dumps(tool_results, indent=2)}

Provide a helpful, concise response to the user's question based on the investigation results.
"""

        try:
            response = self.llm.invoke(synthesis_prompt)
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating legacy response: {e}")
            return self._generate_structured_fallback(user_input, tool_results)
    
    def _generate_structured_fallback(self, user_input: str, tool_results: List[Dict[str, Any]]) -> str:
        """Generate a structured fallback response"""
        output = f"📋 RESPONSE TO: {user_input}\n\n"
        
        for result in tool_results:
            if result.get("success"):
                tool_name = result.get("tool", "unknown")
                summary = result.get("summary", "Completed")
                output += f"✅ {tool_name}: {summary}\n"
                
                # Add specific details based on tool type
                data = result.get("data", {})
                if tool_name == "list_collections" and data.get("collections"):
                    output += f"\nCollections in {data.get('database', 'database')}:\n"
                    for coll in data["collections"]:
                        if "error" not in coll:
                            output += f"• {coll['name']}: {coll['count']:,} documents\n"
                            
                elif tool_name == "list_databases" and data.get("databases"):
                    output += f"\nAvailable databases:\n"
                    for db in data["databases"]:
                        if "error" not in db:
                            output += f"• {db['name']}: {db['collections']} collections\n"
                            
                elif tool_name == "fetch_slow_queries" and data:
                    output += f"\nSlow queries found:\n"
                    for i, query in enumerate(data[:3], 1):  # Show top 3
                        output += f"{i}. {query['collection']}: {query['execution_time_ms']}ms\n"
                        
            else:
                error = result.get("error", "Unknown error")
                output += f"❌ {result.get('tool', 'tool')}: {error}\n"
        
        return output
    
    def investigate(self, user_input: str) -> str:
        """Main investigation with intelligent reasoning and memory"""
        logger.info(f"Starting memory-enabled investigation for: {user_input}")
        start_time = time.time()
        
        try:
            # Step 1: Get memory context
            memory_context = self.memory.get_investigation_context(user_input, "testdb")
            logger.info(f"Retrieved memory context: {memory_context.get('total_investigations', 0)} past investigations")
            
            # Step 2: Understand user intent with memory context
            intent = self.classify_user_intent(user_input, memory_context)
            logger.info(f"Intent classification: {intent['category']} (confidence: {intent['confidence']})")
            
            # Step 3: Handle direct answers (non-database questions)
            if intent["category"] == "DIRECT_ANSWER":
                investigation_time = time.time() - start_time
                response = intent.get("suggested_response", "I'm a MongoDB DBA assistant focused on helping with database tasks.")
                return f"{response}\n\n⏱️  Response time: {investigation_time:.1f} seconds\n💬 Direct response (no database analysis needed)"
            
            # Step 4: Check if requires database analysis
            if not intent["requires_database"]:
                investigation_time = time.time() - start_time
                return f"I don't think this question requires database analysis. Could you clarify what specific database information you're looking for?\n\n⏱️  Response time: {investigation_time:.1f} seconds"
            
            # Step 5: Select appropriate tools with memory awareness
            investigation_plan = self.select_tools_intelligently(user_input, intent)
            logger.info(f"Investigation plan: {len(investigation_plan)} steps")
            
            if not investigation_plan:
                investigation_time = time.time() - start_time
                return f"I'm not sure how to help with that question. Could you be more specific about what database information you need?\n\n⏱️  Response time: {investigation_time:.1f} seconds"
            
            # Step 6: Execute investigation plan
            tool_results = []
            for step in investigation_plan:
                tool_name = step.get("tool")
                parameters = step.get("parameters", {})
                reasoning = step.get("reasoning", "")
                
                logger.info(f"Step {step.get('step', 1)}: {tool_name} - {reasoning}")
                
                result = self.execute_tool(tool_name, parameters)
                tool_results.append(result)
                
                # For simple questions, one tool result might be sufficient
                if len(tool_results) == 1 and intent["category"] == "DATABASE_METADATA":
                    if result.get("success"):
                        break
            
            # Step 7: Generate memory-aware response
            final_response = self.generate_final_response(user_input, intent, tool_results, memory_context)
            
            investigation_time = time.time() - start_time
            
            # Step 8: Store investigation in memory
            self._store_investigation_memory(user_input, intent, tool_results, investigation_time, final_response)
            
            # Add timing and memory info to response
            memory_stats = f"🧠 Memory-enhanced investigation with {len(tool_results)} analysis step(s)"
            if memory_context.get("total_investigations", 0) > 0:
                memory_stats += f" (building on {memory_context['total_investigations']} past investigations)"
            
            final_response += f"\n\n⏱️  Investigation time: {investigation_time:.1f} seconds\n{memory_stats}"
            
            return final_response
            
        except Exception as e:
            investigation_time = time.time() - start_time
            logger.error(f"Memory-enabled investigation failed: {e}")
            return f"I encountered an error while investigating your question: {str(e)}\n\n⏱️  Time: {investigation_time:.1f} seconds\n❌ Please try rephrasing your question."
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics for debugging"""
        return self.memory.get_memory_stats()
    
    def close(self):
        """Clean up resources"""
        try:
            self.memory.close()
            logger.info("Agent resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")