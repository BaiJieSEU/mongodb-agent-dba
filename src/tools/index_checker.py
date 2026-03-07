"""Tool for checking MongoDB indexes and suggesting optimizations"""

import logging
from typing import Dict, Any, List, Optional, Set
from models.query_models import IndexInfo
from utils.mongodb_client import MongoDBManager

logger = logging.getLogger(__name__)


class IndexChecker:
    """Analyzes MongoDB indexes and suggests optimizations"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
    
    def get_collection_indexes(self, db_name: str, collection: str) -> List[IndexInfo]:
        """Get all indexes for a specific collection"""
        indexes = []
        
        try:
            with self.mongo_manager.get_monitored_db(db_name) as db:
                coll = db[collection]
                
                # Get index information
                index_info = coll.list_indexes()
                
                for idx in index_info:
                    try:
                        # Get index stats for usage information (MongoDB 8.x compatible)
                        try:
                            stats = db.command("collStats", collection)
                            index_stats = stats.get("indexSizes", {})
                            size_bytes = index_stats.get(idx["name"], 0)
                        except Exception:
                            # Fallback if stats are not available
                            size_bytes = 0
                        
                        indexes.append(IndexInfo(
                            name=idx["name"],
                            keys=idx["key"],
                            collection=collection,
                            size_bytes=size_bytes
                        ))
                        
                    except Exception as e:
                        logger.warning(f"Could not get stats for index {idx['name']}: {e}")
                        indexes.append(IndexInfo(
                            name=idx["name"],
                            keys=idx["key"],
                            collection=collection
                        ))
                        
        except Exception as e:
            logger.error(f"Error getting indexes for {collection}: {e}")
            
        return indexes
    
    def analyze_query_index_coverage(
        self, 
        db_name: str,
        collection: str,
        query: Dict[str, Any],
        sort: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze if query has proper index coverage"""
        
        analysis = {
            "has_suitable_index": False,
            "matching_indexes": [],
            "missing_fields": [],
            "suggested_index": None,
            "optimization_potential": "unknown"
        }
        
        try:
            # Get existing indexes
            existing_indexes = self.get_collection_indexes(db_name, collection)
            
            # Extract query fields
            query_fields = self._extract_query_fields(query)
            sort_fields = self._extract_sort_fields(sort) if sort else []
            
            # Combine query and sort fields (sort fields should come after query fields)
            all_fields = query_fields + sort_fields
            
            if not all_fields:
                return analysis
            
            # Check existing indexes for coverage
            for index in existing_indexes:
                if index.name == "_id_":
                    continue  # Skip default _id index
                    
                coverage = self._check_index_coverage(index.keys, query_fields, sort_fields)
                if coverage["covers_query"]:
                    analysis["has_suitable_index"] = True
                    analysis["matching_indexes"].append({
                        "name": index.name,
                        "keys": index.keys,
                        "coverage_score": coverage["score"]
                    })
            
            # If no suitable index found, suggest one
            if not analysis["has_suitable_index"]:
                analysis["missing_fields"] = all_fields
                analysis["suggested_index"] = self._suggest_optimal_index(query_fields, sort_fields)
                analysis["optimization_potential"] = "high"
            else:
                # Check if we could optimize existing indexes
                best_match = max(analysis["matching_indexes"], key=lambda x: x["coverage_score"])
                if best_match["coverage_score"] < 1.0:
                    analysis["optimization_potential"] = "medium"
                    analysis["suggested_index"] = self._suggest_optimal_index(query_fields, sort_fields)
                else:
                    analysis["optimization_potential"] = "low"
            
        except Exception as e:
            logger.error(f"Error analyzing index coverage: {e}")
            
        return analysis
    
    def _extract_query_fields(self, query: Dict[str, Any]) -> List[str]:
        """Extract field names from MongoDB query"""
        fields = []
        
        def extract_from_dict(d: Dict[str, Any], path: str = ""):
            for key, value in d.items():
                if key.startswith("$"):
                    # Handle operators
                    if key == "$and" or key == "$or":
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict):
                                    extract_from_dict(item, path)
                    continue
                
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, dict):
                    # Check if it's a query operator or nested document
                    if any(k.startswith("$") for k in value.keys()):
                        # It's a query with operators
                        fields.append(current_path)
                    else:
                        # It's a nested document, recurse
                        extract_from_dict(value, current_path)
                else:
                    # Simple field
                    fields.append(current_path)
        
        if isinstance(query, dict):
            extract_from_dict(query)
        
        return fields
    
    def _extract_sort_fields(self, sort: Dict[str, Any]) -> List[str]:
        """Extract field names from MongoDB sort specification"""
        if not isinstance(sort, dict):
            return []
        
        return list(sort.keys())
    
    def _check_index_coverage(
        self, 
        index_keys: Dict[str, Any], 
        query_fields: List[str], 
        sort_fields: List[str]
    ) -> Dict[str, Any]:
        """Check how well an index covers the query"""
        index_field_names = list(index_keys.keys())
        
        # Check query field coverage
        query_covered = 0
        for field in query_fields:
            if field in index_field_names:
                query_covered += 1
        
        # Check sort field coverage
        sort_covered = 0
        for field in sort_fields:
            if field in index_field_names:
                sort_covered += 1
        
        # Calculate coverage score
        total_fields = len(query_fields) + len(sort_fields)
        if total_fields == 0:
            coverage_score = 0.0
        else:
            coverage_score = (query_covered + sort_covered) / total_fields
        
        # Index covers query if all query fields are covered
        covers_query = query_covered == len(query_fields) and len(query_fields) > 0
        
        return {
            "covers_query": covers_query,
            "query_fields_covered": query_covered,
            "sort_fields_covered": sort_covered,
            "score": coverage_score
        }
    
    def _suggest_optimal_index(self, query_fields: List[str], sort_fields: List[str]) -> Dict[str, Any]:
        """Suggest an optimal index for the given query and sort patterns"""
        # MongoDB index optimization rules:
        # 1. Equality fields first
        # 2. Sort fields next
        # 3. Range fields last
        
        # Check if we have any fields to index
        all_fields = query_fields + sort_fields
        if not all_fields:
            # No specific fields identified - cannot suggest meaningful index
            return {
                "keys": {},
                "command": None,  # No index command for fieldless queries
                "reasoning": "No specific fields identified for indexing (e.g., $where queries, collection scans)"
            }
        
        # Build compound index with query fields first, then sort fields
        suggested_keys = {}
        
        # Add query fields (assuming ascending order)
        for field in query_fields:
            if field not in suggested_keys:
                suggested_keys[field] = 1
        
        # Add sort fields
        for field in sort_fields:
            if field not in suggested_keys:
                suggested_keys[field] = 1  # Will be overridden with actual sort direction if needed
        
        return {
            "keys": suggested_keys,
            "command": f"db.collection.createIndex({suggested_keys})",
            "reasoning": "Compound index covering query fields first, then sort fields"
        }
    
    def find_unused_indexes(self, db_name: str, collection: str) -> List[IndexInfo]:
        """Find potentially unused indexes (requires MongoDB 3.2+)"""
        unused_indexes = []
        
        try:
            with self.mongo_manager.get_monitored_db(db_name) as db:
                # Get index usage stats
                stats = db.command("aggregate", collection, pipeline=[
                    {"$indexStats": {}}
                ])
                
                index_usage = {}
                for stat in stats.get("cursor", {}).get("firstBatch", []):
                    index_name = stat["name"]
                    access_count = stat["accesses"]["ops"]
                    index_usage[index_name] = access_count
                
                # Get all indexes
                indexes = self.get_collection_indexes(db_name, collection)
                
                # Find unused indexes (excluding _id_)
                for index in indexes:
                    if index.name == "_id_":
                        continue
                        
                    usage_count = index_usage.get(index.name, 0)
                    if usage_count == 0:
                        unused_indexes.append(index)
                        
        except Exception as e:
            logger.warning(f"Could not get index usage stats: {e}")
            
        return unused_indexes
    
    def suggest_missing_indexes_for_queries(
        self, 
        db_name: str, 
        queries_info: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze multiple queries and suggest missing indexes"""
        suggestions = []
        
        # Group queries by collection
        queries_by_collection = {}
        for query_info in queries_info:
            collection = query_info.get("collection")
            if collection:
                if collection not in queries_by_collection:
                    queries_by_collection[collection] = []
                queries_by_collection[collection].append(query_info)
        
        # Analyze each collection
        for collection, queries in queries_by_collection.items():
            try:
                collection_suggestions = []
                
                for query_info in queries:
                    query = query_info.get("query", {})
                    sort = query_info.get("sort")
                    
                    analysis = self.analyze_query_index_coverage(
                        db_name, collection, query, sort
                    )
                    
                    if not analysis["has_suitable_index"] and analysis["suggested_index"]:
                        suggestion = {
                            "collection": collection,
                            "query_pattern": query,
                            "current_performance": {
                                "execution_time_ms": query_info.get("execution_time_ms", 0),
                                "docs_examined": query_info.get("docs_examined", 0)
                            },
                            "suggested_index": analysis["suggested_index"],
                            "optimization_potential": analysis["optimization_potential"],
                            "priority": self._calculate_priority(query_info, analysis)
                        }
                        collection_suggestions.append(suggestion)
                
                # Remove duplicate index suggestions
                unique_suggestions = self._deduplicate_index_suggestions(collection_suggestions)
                suggestions.extend(unique_suggestions)
                
            except Exception as e:
                logger.error(f"Error analyzing collection {collection}: {e}")
                continue
        
        return suggestions
    
    def _calculate_priority(self, query_info: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Calculate priority level for index suggestion"""
        execution_time = query_info.get("execution_time_ms", 0)
        docs_examined = query_info.get("docs_examined", 0)
        docs_returned = query_info.get("docs_returned", 1)
        
        # Calculate examination ratio
        exam_ratio = docs_examined / max(docs_returned, 1)
        
        if execution_time > 1000 or exam_ratio > 1000:
            return "critical"
        elif execution_time > 500 or exam_ratio > 100:
            return "high"
        elif execution_time > 100 or exam_ratio > 10:
            return "medium"
        else:
            return "low"
    
    def _deduplicate_index_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate index suggestions for the same collection"""
        seen_indexes = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            # Skip suggestions with empty or no index keys (e.g., $where queries)
            suggested_index = suggestion.get("suggested_index", {})
            index_keys = suggested_index.get("keys", {})
            
            if not index_keys:
                # No meaningful index suggestion - skip deduplication 
                continue
                
            index_key = str(index_keys)
            collection = suggestion["collection"]
            
            key = f"{collection}:{index_key}"
            if key not in seen_indexes:
                seen_indexes.add(key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions


def create_index_checker_tool(mongo_manager: MongoDBManager):
    """Create LangChain tool for index analysis"""
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
    import json
    
    class IndexCheckInput(BaseModel):
        db_name: str = Field(description="Database name")
        collection: str = Field(description="Collection name")
        query: str = Field(description="MongoDB query as JSON string")
        sort: Optional[str] = Field(None, description="Sort specification as JSON string")
    
    checker = IndexChecker(mongo_manager)
    
    def check_indexes_tool(db_name: str, collection: str, query: str, sort: str = None) -> str:
        """Check indexes for a query and suggest optimizations"""
        try:
            query_dict = json.loads(query) if isinstance(query, str) else query
            sort_dict = json.loads(sort) if sort else None
            
            # Get existing indexes
            existing_indexes = checker.get_collection_indexes(db_name, collection)
            
            # Analyze query coverage
            analysis = checker.analyze_query_index_coverage(
                db_name, collection, query_dict, sort_dict
            )
            
            result = f"Index Analysis for {collection}:\n\n"
            
            # Show existing indexes
            result += "Existing Indexes:\n"
            for idx in existing_indexes:
                result += f"- {idx.name}: {idx.keys}\n"
            result += "\n"
            
            # Show query analysis
            result += f"Query: {json.dumps(query_dict, indent=2)}\n"
            if sort_dict:
                result += f"Sort: {json.dumps(sort_dict, indent=2)}\n"
            result += "\n"
            
            result += f"Index Coverage Analysis:\n"
            result += f"- Has suitable index: {analysis['has_suitable_index']}\n"
            result += f"- Optimization potential: {analysis['optimization_potential']}\n"
            
            if analysis["matching_indexes"]:
                result += f"- Matching indexes:\n"
                for idx in analysis["matching_indexes"]:
                    result += f"  * {idx['name']} (coverage: {idx['coverage_score']:.2f})\n"
            
            if analysis["suggested_index"]:
                result += f"\nRecommended Index:\n"
                suggested = analysis["suggested_index"]
                result += f"Command: db.{collection}.createIndex({suggested['keys']})\n"
                result += f"Reasoning: {suggested['reasoning']}\n"
            
            return result
            
        except Exception as e:
            return f"Error checking indexes: {str(e)}"
    
    return StructuredTool(
        name="check_indexes",
        description="Analyze indexes for a query and suggest optimizations",
        func=check_indexes_tool,
        args_schema=IndexCheckInput
    )