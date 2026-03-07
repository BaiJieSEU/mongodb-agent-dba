"""Tool for fetching slow queries from MongoDB profiler"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.query_models import SlowQuery
from utils.mongodb_client import MongoDBManager

logger = logging.getLogger(__name__)


class SlowQueryFetcher:
    """Fetches slow queries from MongoDB profiler collection"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
    
    def fetch_slow_queries(
        self, 
        db_name: str,
        threshold_ms: int = 100,
        limit: int = 50,
        hours_back: int = 2  # Now represents relative window from most recent
    ) -> List[SlowQuery]:
        """
        Fetch slow queries from system.profile collection using recent-query anchored time window
        
        NEW LOGIC: Finds most recent slow query, then looks back N hours from that point.
        This ensures agent works regardless of when it's triggered (demo-robust).
        
        Args:
            db_name: Database name to analyze
            threshold_ms: Minimum execution time in milliseconds  
            limit: Maximum number of queries to return
            hours_back: Hours to look back from MOST RECENT slow query (not from now)
            
        Returns:
            List of SlowQuery objects (deduplicated)
        """
        slow_queries = []
        
        try:
            # Enable profiler if not already enabled with correct threshold
            self.mongo_manager.ensure_profiler_enabled(db_name, level=1, threshold_ms=threshold_ms)
            
            with self.mongo_manager.get_monitored_db(db_name) as db:
                # STEP 1: Find the most recent slow query to use as anchor point
                most_recent_query = db["system.profile"].find_one(
                    {
                        "millis": {"$gte": threshold_ms},
                        "op": {"$in": ["command", "query", "findAndModify", "update", "remove"]},
                        # Exclude system operations and admin commands
                        "ns": {"$not": {"$regex": "^" + db_name + r"\.(system\.|tmp\.mr\.)"}},
                        "command.createIndexes": {"$exists": False},
                        "command.dropIndexes": {"$exists": False},
                        "command.reIndex": {"$exists": False},
                        "command.collMod": {"$exists": False},
                        "command.explain": {"$exists": False},
                        "command.profile": {"$exists": False}
                    },
                    sort=[("ts", -1)]  # Most recent first
                )
                
                if not most_recent_query:
                    logger.info(f"No slow queries found in {db_name} profiler collection")
                    return []
                
                # STEP 2: Calculate relative time window from most recent query
                anchor_time = most_recent_query.get("ts")
                if not anchor_time:
                    logger.warning("Most recent query has no timestamp, falling back to current time")
                    anchor_time = datetime.utcnow()
                
                start_time = anchor_time - timedelta(hours=hours_back)
                end_time = anchor_time
                
                logger.info(f"Using time window: {start_time} to {end_time} (anchored to most recent query)")
                
                # STEP 3: Fetch all slow queries in the relative time window
                profile_filter = {
                    "ts": {"$gte": start_time, "$lte": end_time},
                    "millis": {"$gte": threshold_ms},
                    "op": {"$in": ["command", "query", "findAndModify", "update", "remove"]},
                    # Exclude system operations
                    "ns": {"$not": {"$regex": "^" + db_name + r"\.(system\.|tmp\.mr\.)"}},
                    # Exclude administrative commands
                    "command.createIndexes": {"$exists": False},
                    "command.dropIndexes": {"$exists": False},
                    "command.reIndex": {"$exists": False},
                    "command.collMod": {"$exists": False},
                    # Exclude explain commands from agent investigation
                    "command.explain": {"$exists": False},
                    # Exclude profiler status checks
                    "command.profile": {"$exists": False}
                }
                
                profile_cursor = db["system.profile"].find(profile_filter).sort("millis", -1).limit(limit * 2)  # Fetch more for deduplication
                
                # STEP 4: Parse and deduplicate queries
                raw_queries = []
                for doc in profile_cursor:
                    try:
                        slow_query = self._parse_profile_doc(doc, db_name)
                        if slow_query:
                            raw_queries.append(slow_query)
                    except Exception as e:
                        logger.warning(f"Failed to parse profile document: {e}")
                        continue
                
                # STEP 5: Deduplicate similar query patterns
                slow_queries = self._deduplicate_queries(raw_queries, limit)
                        
                logger.info(f"Found {len(slow_queries)} slow queries in {db_name} (after deduplication)")
                
        except Exception as e:
            logger.error(f"Error fetching slow queries from {db_name}: {e}")
            
        return slow_queries
    
    def _parse_profile_doc(self, doc: Dict[str, Any], db_name: str) -> Optional[SlowQuery]:
        """Parse a MongoDB profiler document into SlowQuery object"""
        try:
            # Extract collection name from namespace
            namespace = doc.get("ns", "")
            if "." in namespace:
                collection = namespace.split(".", 1)[1]
            else:
                collection = "unknown"
            
            # Extract query information
            command = doc.get("command", {})
            query = {}
            
            # Handle different command types and extract actual query patterns
            if "explain" in command:
                # Extract query from explain command
                explain_cmd = command["explain"]
                if "filter" in explain_cmd:
                    query = explain_cmd["filter"]
                elif "find" in explain_cmd:
                    query = explain_cmd.get("filter", {})
                elif "aggregate" in explain_cmd:
                    pipeline = explain_cmd.get("pipeline", [])
                    # Extract $match stages from pipeline
                    matches = [stage.get("$match", {}) for stage in pipeline if "$match" in stage]
                    query = matches[0] if matches else {}
            elif "filter" in command:
                query = command["filter"]
            elif "q" in command:
                query = command["q"]
            elif "query" in command:
                query = command["query"]
            elif "find" in command:
                # For find operations, the collection name might be in find
                query = command.get("filter", {})
            elif "aggregate" in command:
                # Extract $match from aggregation pipeline
                pipeline = command.get("pipeline", [])
                matches = [stage.get("$match", {}) for stage in pipeline if "$match" in stage]
                query = matches[0] if matches else {}
            
            # Get execution statistics
            execution_time = doc.get("millis", 0)
            docs_examined = doc.get("docsExamined", 0)
            docs_returned = doc.get("nreturned", 0)
            
            # Extract index information
            execution_stats = doc.get("executionStats", {})
            index_used = None
            if execution_stats:
                winning_plan = execution_stats.get("executionStats", {}).get("winningPlan", {})
                if "indexName" in winning_plan:
                    index_used = winning_plan["indexName"]
            
            return SlowQuery(
                timestamp=doc.get("ts", datetime.utcnow()),
                collection=collection,
                operation=doc.get("op", "unknown"),
                query=query,
                execution_time_ms=execution_time,
                docs_examined=docs_examined,
                docs_returned=docs_returned,
                index_used=index_used
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse profile document: {e}")
            return None
    
    def get_recent_slow_queries_summary(self, db_name: str, threshold_ms: int = 100) -> Dict[str, Any]:
        """Get a summary of recent slow queries for quick analysis"""
        slow_queries = self.fetch_slow_queries(db_name, threshold_ms, limit=100)
        
        if not slow_queries:
            return {
                "total_queries": 0,
                "collections_affected": [],
                "avg_execution_time": 0,
                "max_execution_time": 0,
                "summary": "No slow queries found"
            }
        
        # Analyze patterns
        collections = list(set(q.collection for q in slow_queries))
        execution_times = [q.execution_time_ms for q in slow_queries]
        
        summary = {
            "total_queries": len(slow_queries),
            "collections_affected": collections,
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "max_execution_time": max(execution_times),
            "queries_by_collection": {},
            "summary": f"Found {len(slow_queries)} slow queries across {len(collections)} collections"
        }
        
        # Group by collection
        for collection in collections:
            collection_queries = [q for q in slow_queries if q.collection == collection]
            summary["queries_by_collection"][collection] = {
                "count": len(collection_queries),
                "avg_time": sum(q.execution_time_ms for q in collection_queries) / len(collection_queries)
            }
        
        return summary
    
    def _deduplicate_queries(self, queries: List[SlowQuery], limit: int) -> List[SlowQuery]:
        """
        Deduplicate similar query patterns while preserving diversity
        
        Args:
            queries: List of raw slow queries
            limit: Maximum number of queries to return
            
        Returns:
            Deduplicated list of slow queries
        """
        if not queries:
            return []
        
        # Group queries by pattern for deduplication
        pattern_groups = {}
        
        for query in queries:
            # Create a pattern key for grouping similar queries
            pattern_key = self._create_pattern_key(query)
            
            if pattern_key not in pattern_groups:
                pattern_groups[pattern_key] = []
            pattern_groups[pattern_key].append(query)
        
        # Select the best representative from each pattern group
        deduplicated = []
        
        # Sort pattern groups by their worst (slowest) query time
        sorted_patterns = sorted(
            pattern_groups.items(), 
            key=lambda x: max(q.execution_time_ms for q in x[1]), 
            reverse=True
        )
        
        for pattern_key, group_queries in sorted_patterns:
            if len(deduplicated) >= limit:
                break
                
            # Choose the slowest query from this pattern group as representative
            representative = max(group_queries, key=lambda q: q.execution_time_ms)
            deduplicated.append(representative)
            
            # Log deduplication info
            if len(group_queries) > 1:
                logger.debug(f"Deduplicated {len(group_queries)} queries with pattern: {pattern_key}")
        
        logger.info(f"Deduplication: {len(queries)} -> {len(deduplicated)} queries across {len(pattern_groups)} patterns")
        return deduplicated
    
    def _create_pattern_key(self, query: SlowQuery) -> str:
        """
        Create a pattern key for grouping similar queries
        
        Args:
            query: SlowQuery object
            
        Returns:
            Pattern key string for grouping
        """
        # Combine collection, operation, and normalized query structure
        pattern_parts = [
            f"collection:{query.collection}",
            f"operation:{query.operation}"
        ]
        
        # Normalize query structure for pattern matching
        if query.query:
            normalized_query = self._normalize_query_structure(query.query)
            pattern_parts.append(f"query:{normalized_query}")
        
        return "|".join(pattern_parts)
    
    def _normalize_query_structure(self, query: Dict) -> str:
        """
        Normalize query structure to identify patterns while ignoring specific values
        
        Args:
            query: Query dictionary
            
        Returns:
            Normalized query structure string
        """
        if not query:
            return "empty"
        
        # For simple field queries, just use the field names
        if isinstance(query, dict):
            # Handle special operators
            if "$where" in query:
                return "$where"
            
            # For regular field queries, extract field names and operators
            normalized_parts = []
            for field, value in query.items():
                if isinstance(value, dict):
                    # Handle operator queries like {age: {$gt: 30}}
                    operators = list(value.keys())
                    normalized_parts.append(f"{field}:{'+'.join(operators)}")
                else:
                    # Simple equality queries like {email: "user@example.com"}
                    normalized_parts.append(f"{field}:eq")
            
            return "{" + ",".join(sorted(normalized_parts)) + "}"
        
        return str(type(query).__name__)


def create_slow_query_fetcher_tool(mongo_manager: MongoDBManager):
    """Create LangChain tool for slow query fetching"""
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
    
    class SlowQueryInput(BaseModel):
        db_name: str = Field(description="Database name to analyze")
        threshold_ms: int = Field(default=100, description="Minimum execution time threshold in ms")
        limit: int = Field(default=20, description="Maximum number of queries to fetch")
    
    fetcher = SlowQueryFetcher(mongo_manager)
    
    def fetch_slow_queries_tool(db_name: str, threshold_ms: int = 100, limit: int = 20) -> str:
        """Fetch slow queries from MongoDB profiler collection"""
        try:
            queries = fetcher.fetch_slow_queries(db_name, threshold_ms, limit)
            summary = fetcher.get_recent_slow_queries_summary(db_name, threshold_ms)
            
            if not queries:
                return f"No slow queries found in database '{db_name}' with threshold {threshold_ms}ms"
            
            result = f"Found {len(queries)} slow queries in '{db_name}':\n\n"
            result += f"Summary: {summary['summary']}\n"
            result += f"Collections affected: {', '.join(summary['collections_affected'])}\n"
            result += f"Average execution time: {summary['avg_execution_time']:.1f}ms\n\n"
            
            # Show top 5 slowest queries with details
            top_queries = sorted(queries, key=lambda x: x.execution_time_ms, reverse=True)[:5]
            result += "Top slow queries:\n"
            
            for i, query in enumerate(top_queries, 1):
                result += f"{i}. Collection: {query.collection}\n"
                result += f"   Execution time: {query.execution_time_ms}ms\n"
                result += f"   Docs examined: {query.docs_examined}, returned: {query.docs_returned}\n"
                result += f"   Query: {query.query}\n"
                result += f"   Index used: {query.index_used or 'None'}\n\n"
            
            return result
            
        except Exception as e:
            return f"Error fetching slow queries: {str(e)}"
    
    return StructuredTool(
        name="fetch_slow_queries",
        description="Fetch slow queries from MongoDB profiler collection for analysis",
        func=fetch_slow_queries_tool,
        args_schema=SlowQueryInput
    )