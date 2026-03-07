"""Tool for explaining MongoDB queries and analyzing execution plans"""

import logging
from typing import Dict, Any, Optional, List
from models.query_models import ExplainPlan
from utils.mongodb_client import MongoDBManager

logger = logging.getLogger(__name__)


class QueryExplainer:
    """Analyzes MongoDB queries using explain() plans"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
    
    def explain_query(
        self,
        db_name: str,
        collection: str,
        query: Dict[str, Any],
        explain_mode: str = "executionStats"
    ) -> Optional[ExplainPlan]:
        """
        Execute explain() on a MongoDB query
        
        Args:
            db_name: Database name
            collection: Collection name
            query: MongoDB query document
            explain_mode: Explain verbosity mode
            
        Returns:
            ExplainPlan object with execution statistics
        """
        try:
            with self.mongo_manager.get_monitored_db(db_name) as db:
                coll = db[collection]
                
                # Execute explain with timing
                import time
                start_time = time.time()
                # MongoDB 8.x compatibility - explain() takes no arguments
                try:
                    explain_result = coll.find(query).explain()
                except TypeError:
                    # Fallback for older versions
                    explain_result = coll.find(query).explain(explain_mode)
                end_time = time.time()
                
                # Parse the explain output
                return self._parse_explain_result(
                    explain_result, query, collection, (end_time - start_time) * 1000
                )
                
        except Exception as e:
            logger.error(f"Error explaining query: {e}")
            return None
    
    def _parse_explain_result(
        self, 
        explain_result: Dict[str, Any], 
        query: Dict[str, Any],
        collection: str,
        execution_time_ms: float
    ) -> ExplainPlan:
        """Parse MongoDB explain output into ExplainPlan object"""
        
        execution_stats = explain_result.get("executionStats", {})
        query_planner = explain_result.get("queryPlanner", {})
        
        # Extract key metrics  
        total_docs_examined = execution_stats.get("totalDocsExamined", 0)
        total_docs_returned = execution_stats.get("nReturned", execution_stats.get("totalDocsReturned", 0))
        execution_time = execution_stats.get("executionTimeMillis", int(execution_time_ms))
        
        # Determine index usage and stage (check multiple locations for compatibility)
        index_used = None
        stage = "UNKNOWN"
        winning_plan = None
        
        # First try executionStats.executionStages (newer format)
        execution_stages = execution_stats.get("executionStages", {})
        if execution_stages and isinstance(execution_stages, dict):
            stage = execution_stages.get("stage", "UNKNOWN")
            if stage == "IXSCAN":
                index_used = execution_stages.get("indexName")
            winning_plan = execution_stages
        
        # Fallback to queryPlanner.winningPlan (also newer format)
        elif query_planner:
            winning_plan = query_planner.get("winningPlan", {})
            if winning_plan:
                stage = winning_plan.get("stage", "UNKNOWN")
                if stage == "IXSCAN":
                    index_used = winning_plan.get("indexName")
                elif "inputStage" in winning_plan:
                    # Check nested stages for index usage
                    input_stage = winning_plan["inputStage"]
                    while input_stage:
                        if input_stage.get("stage") == "IXSCAN":
                            index_used = input_stage.get("indexName")
                            break
                        input_stage = input_stage.get("inputStage")
        
        # Legacy fallback to top-level winningPlan (older MongoDB versions)
        else:
            winning_plan = explain_result.get("winningPlan", {})
            if winning_plan:
                stage = winning_plan.get("stage", "UNKNOWN")
                if stage == "IXSCAN":
                    index_used = winning_plan.get("indexName")
        
        # Ensure we have a default winning_plan for the return statement
        if not winning_plan:
            winning_plan = {}
        
        return ExplainPlan(
            query=query,
            collection=collection,
            execution_stats=execution_stats,
            winning_plan=winning_plan,
            execution_time_ms=execution_time,
            total_docs_examined=total_docs_examined,
            total_docs_returned=total_docs_returned,
            index_used=index_used,
            stage=stage
        )
    
    def analyze_query_performance(self, explain_plan: ExplainPlan) -> Dict[str, Any]:
        """Analyze query performance and identify issues"""
        analysis = {
            "performance_issues": [],
            "efficiency_ratio": 0.0,
            "index_effectiveness": "unknown",
            "recommendations": []
        }
        
        if explain_plan.total_docs_returned > 0:
            # Calculate efficiency ratio (docs returned / docs examined)
            analysis["efficiency_ratio"] = (
                explain_plan.total_docs_returned / max(explain_plan.total_docs_examined, 1)
            )
        
        # Analyze performance issues
        if explain_plan.stage == "COLLSCAN":
            analysis["performance_issues"].append({
                "type": "collection_scan",
                "severity": "high",
                "description": "Query performs full collection scan",
                "impact": "High CPU and I/O usage, poor performance with large collections"
            })
            analysis["recommendations"].append("Consider adding an index for this query pattern")
        
        if explain_plan.total_docs_examined > explain_plan.total_docs_returned * 10:
            analysis["performance_issues"].append({
                "type": "high_examination_ratio",
                "severity": "medium",
                "description": f"Query examines {explain_plan.total_docs_examined} docs but returns only {explain_plan.total_docs_returned}",
                "impact": "Inefficient query execution, excessive I/O"
            })
            analysis["recommendations"].append("Optimize query selectivity or add more specific indexes")
        
        if explain_plan.execution_time_ms > 1000:
            analysis["performance_issues"].append({
                "type": "slow_execution",
                "severity": "high",
                "description": f"Query execution time: {explain_plan.execution_time_ms}ms",
                "impact": "Poor user experience, potential application timeouts"
            })
        
        # Index effectiveness analysis
        if explain_plan.index_used:
            if analysis["efficiency_ratio"] > 0.1:
                analysis["index_effectiveness"] = "good"
            else:
                analysis["index_effectiveness"] = "poor"
                analysis["recommendations"].append("Consider optimizing index or query structure")
        else:
            analysis["index_effectiveness"] = "none"
            analysis["recommendations"].append("Add appropriate index for this query")
        
        return analysis
    
    def batch_explain_queries(
        self, 
        db_name: str, 
        queries_info: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Explain multiple queries and return analysis results"""
        results = []
        
        for query_info in queries_info:
            collection = query_info.get("collection")
            query = query_info.get("query", {})
            
            if not collection or not query:
                continue
                
            try:
                explain_plan = self.explain_query(db_name, collection, query)
                if explain_plan:
                    analysis = self.analyze_query_performance(explain_plan)
                    
                    results.append({
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
                logger.error(f"Error explaining query for {collection}: {e}")
                continue
        
        return results


def create_query_explainer_tool(mongo_manager: MongoDBManager):
    """Create LangChain tool for query explanation"""
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
    import json
    
    class ExplainQueryInput(BaseModel):
        db_name: str = Field(description="Database name")
        collection: str = Field(description="Collection name")
        query: str = Field(description="MongoDB query as JSON string")
    
    explainer = QueryExplainer(mongo_manager)
    
    def explain_query_tool(db_name: str, collection: str, query: str) -> str:
        """Explain a MongoDB query and analyze its performance"""
        try:
            # Parse query JSON
            query_dict = json.loads(query) if isinstance(query, str) else query
            
            explain_plan = explainer.explain_query(db_name, collection, query_dict)
            if not explain_plan:
                return f"Failed to explain query for {collection}"
            
            analysis = explainer.analyze_query_performance(explain_plan)
            
            result = f"Query Explanation for {collection}:\n\n"
            result += f"Query: {json.dumps(query_dict, indent=2)}\n\n"
            result += f"Execution Statistics:\n"
            result += f"- Execution time: {explain_plan.execution_time_ms}ms\n"
            result += f"- Documents examined: {explain_plan.total_docs_examined:,}\n"
            result += f"- Documents returned: {explain_plan.total_docs_returned:,}\n"
            result += f"- Efficiency ratio: {analysis['efficiency_ratio']:.3f}\n"
            result += f"- Execution stage: {explain_plan.stage}\n"
            result += f"- Index used: {explain_plan.index_used or 'None'}\n\n"
            
            if analysis["performance_issues"]:
                result += "Performance Issues Found:\n"
                for issue in analysis["performance_issues"]:
                    result += f"- {issue['type'].upper()} ({issue['severity']}): {issue['description']}\n"
                result += "\n"
            
            if analysis["recommendations"]:
                result += "Recommendations:\n"
                for rec in analysis["recommendations"]:
                    result += f"- {rec}\n"
            
            return result
            
        except Exception as e:
            return f"Error explaining query: {str(e)}"
    
    return StructuredTool(
        name="explain_query",
        description="Explain a MongoDB query and analyze its execution performance",
        func=explain_query_tool,
        args_schema=ExplainQueryInput
    )