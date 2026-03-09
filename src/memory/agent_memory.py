"""MongoDB-based memory layer for DBA Agent"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from bson import ObjectId

logger = logging.getLogger(__name__)


@dataclass
class Investigation:
    """Represents a single investigation in agent memory"""
    investigation_id: str
    timestamp: datetime
    user_query: str
    intent_category: str  # DIRECT_ANSWER, DATABASE_METADATA, PERFORMANCE_ANALYSIS
    database_analyzed: str
    tools_used: List[str]
    findings: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    recommendations_implemented: bool = False
    follow_up_needed: bool = False
    investigation_time_seconds: float = 0.0
    expires_at: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        # Convert datetime objects to ensure proper MongoDB storage
        if self.expires_at:
            data['expires_at'] = self.expires_at
        return data


@dataclass
class PerformanceIssue:
    """Tracks specific performance issues over time"""
    issue_id: str  # Hash of query + collection 
    database: str
    collection: str
    query_pattern: str
    query_hash: str
    first_detected: datetime
    last_detected: datetime
    detection_count: int
    avg_execution_time_ms: float
    recommended_action: str
    action_implemented: bool = False
    severity: str = "medium"  # low, medium, high, critical
    expires_at: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = asdict(self)
        if self.expires_at:
            data['expires_at'] = self.expires_at
        return data


@dataclass
class UserContext:
    """Tracks user interaction patterns and preferences"""
    user_id: str = "default_user"  # For future multi-user support
    preferred_detail_level: str = "medium"  # brief, medium, detailed
    common_databases: List[str] = None
    investigation_history_summary: Dict[str, Any] = None
    last_activity: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return asdict(self)


class AgentMemory:
    """MongoDB-based memory management for DBA Agent"""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017", 
                 database_name: str = "agent_memory"):
        self.client = MongoClient(connection_string)
        self.db = self.client[database_name]
        
        # Collections
        self.investigations: Collection = self.db.investigations
        self.performance_issues: Collection = self.db.performance_issues  
        self.user_context: Collection = self.db.user_context
        
        # Initialize indexes and TTL
        self._ensure_indexes()
        
        logger.info(f"Agent memory initialized with database: {database_name}")
    
    def _ensure_indexes(self):
        """Create indexes for efficient querying and automatic expiration"""
        
        # Investigations collection indexes
        self.investigations.create_index([
            ("timestamp", DESCENDING)
        ], name="timestamp_desc")
        
        self.investigations.create_index([
            ("database_analyzed", ASCENDING),
            ("intent_category", ASCENDING),
            ("timestamp", DESCENDING)
        ], name="database_intent_time")
        
        self.investigations.create_index([
            ("user_query", "text"),
            ("findings", "text"),
            ("recommendations", "text")
        ], name="text_search")
        
        # TTL index for automatic expiration (30 days)
        self.investigations.create_index([
            ("expires_at", ASCENDING)
        ], expireAfterSeconds=0, name="investigations_ttl")
        
        # Performance issues collection indexes
        self.performance_issues.create_index([
            ("database", ASCENDING),
            ("collection", ASCENDING),
            ("last_detected", DESCENDING)
        ], name="db_collection_time")
        
        self.performance_issues.create_index([
            ("query_hash", ASCENDING)
        ], unique=True, name="query_hash_unique")
        
        self.performance_issues.create_index([
            ("severity", ASCENDING),
            ("action_implemented", ASCENDING),
            ("last_detected", DESCENDING)
        ], name="severity_status_time")
        
        # TTL index for performance issues (90 days)
        self.performance_issues.create_index([
            ("expires_at", ASCENDING)
        ], expireAfterSeconds=0, name="performance_issues_ttl")
        
        # User context indexes
        self.user_context.create_index([
            ("user_id", ASCENDING)
        ], unique=True, name="user_id_unique")
        
        logger.info("Memory indexes created successfully")
    
    def store_investigation(self, investigation: Investigation) -> str:
        """Store a new investigation in memory"""
        try:
            # Set expiration date (30 days from now)
            investigation.expires_at = datetime.utcnow() + timedelta(days=30)
            
            result = self.investigations.insert_one(investigation.to_dict())
            investigation_oid = str(result.inserted_id)
            
            logger.info(f"Stored investigation: {investigation_oid}")
            return investigation_oid
            
        except Exception as e:
            logger.error(f"Error storing investigation: {e}")
            raise
    
    def store_performance_issue(self, issue: PerformanceIssue) -> str:
        """Store or update a performance issue"""
        try:
            # Set expiration date (90 days from now)
            issue.expires_at = datetime.utcnow() + timedelta(days=90)
            
            # Try to update existing issue, or insert new one
            issue_dict = issue.to_dict()
            # Remove detection_count from $set to avoid conflict
            if "detection_count" in issue_dict:
                del issue_dict["detection_count"]
                
            result = self.performance_issues.update_one(
                {"query_hash": issue.query_hash},
                {
                    "$set": issue_dict,
                    "$inc": {"detection_count": 1},
                    "$setOnInsert": {
                        "first_detected": issue.first_detected
                    }
                },
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"Stored new performance issue: {issue.issue_id}")
                return str(result.upserted_id)
            else:
                logger.info(f"Updated existing performance issue: {issue.issue_id}")
                return issue.issue_id
                
        except Exception as e:
            logger.error(f"Error storing performance issue: {e}")
            raise
    
    def get_recent_investigations(self, database: str = None, 
                                 limit: int = 5, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get recent investigations for context"""
        try:
            query = {
                "timestamp": {"$gte": datetime.utcnow() - timedelta(days=days_back)}
            }
            
            if database:
                query["database_analyzed"] = database
            
            cursor = self.investigations.find(query).sort("timestamp", DESCENDING).limit(limit)
            investigations = list(cursor)
            
            logger.info(f"Retrieved {len(investigations)} recent investigations")
            return investigations
            
        except Exception as e:
            logger.error(f"Error retrieving recent investigations: {e}")
            return []
    
    def get_recurring_performance_issues(self, database: str = None, 
                                       min_detections: int = 2) -> List[Dict[str, Any]]:
        """Get performance issues that have been detected multiple times"""
        try:
            query = {
                "detection_count": {"$gte": min_detections},
                "action_implemented": False
            }
            
            if database:
                query["database"] = database
            
            cursor = self.performance_issues.find(query).sort("detection_count", DESCENDING)
            issues = list(cursor)
            
            logger.info(f"Retrieved {len(issues)} recurring performance issues")
            return issues
            
        except Exception as e:
            logger.error(f"Error retrieving recurring issues: {e}")
            return []
    
    def mark_recommendation_implemented(self, investigation_id: str = None, 
                                     performance_issue_id: str = None):
        """Mark recommendations as implemented"""
        try:
            if investigation_id:
                self.investigations.update_one(
                    {"_id": ObjectId(investigation_id)},
                    {"$set": {"recommendations_implemented": True}}
                )
                logger.info(f"Marked investigation {investigation_id} recommendations as implemented")
            
            if performance_issue_id:
                self.performance_issues.update_one(
                    {"issue_id": performance_issue_id},
                    {"$set": {"action_implemented": True}}
                )
                logger.info(f"Marked performance issue {performance_issue_id} as resolved")
                
        except Exception as e:
            logger.error(f"Error marking recommendation as implemented: {e}")
    
    def find_similar_past_issues(self, query_pattern: str, collection: str, 
                               database: str = None) -> List[Dict[str, Any]]:
        """Find similar issues from the past"""
        try:
            query = {
                "collection": collection,
                "$text": {"$search": query_pattern}
            }
            
            if database:
                query["database"] = database
            
            cursor = self.performance_issues.find(query).sort("last_detected", DESCENDING)
            similar_issues = list(cursor)
            
            logger.info(f"Found {len(similar_issues)} similar past issues")
            return similar_issues
            
        except Exception as e:
            logger.error(f"Error finding similar issues: {e}")
            return []
    
    def get_investigation_context(self, user_query: str, database: str = "testdb") -> Dict[str, Any]:
        """Get relevant context for a new investigation"""
        try:
            context = {
                "recent_investigations": self.get_recent_investigations(database, limit=3),
                "recurring_issues": self.get_recurring_performance_issues(database, min_detections=2),
                "total_investigations": self.investigations.count_documents(
                    {"database_analyzed": database}
                ),
                "unresolved_issues": self.performance_issues.count_documents({
                    "database": database,
                    "action_implemented": False
                })
            }
            
            # Add query-specific context
            if "slow" in user_query.lower() or "performance" in user_query.lower():
                # For performance questions, get recent performance data
                context["recent_performance_investigations"] = list(
                    self.investigations.find({
                        "database_analyzed": database,
                        "intent_category": "PERFORMANCE_ANALYSIS",
                        "timestamp": {"$gte": datetime.utcnow() - timedelta(days=14)}
                    }).sort("timestamp", DESCENDING).limit(3)
                )
            
            logger.info(f"Built investigation context with {len(context)} elements")
            return context
            
        except Exception as e:
            logger.error(f"Error building investigation context: {e}")
            return {}
    
    def cleanup_expired_memory(self):
        """Manual cleanup of expired memory (TTL handles this automatically)"""
        try:
            now = datetime.utcnow()
            
            # Remove expired investigations
            investigations_deleted = self.investigations.delete_many({
                "expires_at": {"$lt": now}
            }).deleted_count
            
            # Remove expired performance issues
            issues_deleted = self.performance_issues.delete_many({
                "expires_at": {"$lt": now}
            }).deleted_count
            
            logger.info(f"Cleanup: removed {investigations_deleted} investigations, "
                       f"{issues_deleted} performance issues")
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
        logger.info("Agent memory connection closed")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memory"""
        try:
            stats = {
                "total_investigations": self.investigations.count_documents({}),
                "recent_investigations": self.investigations.count_documents({
                    "timestamp": {"$gte": datetime.utcnow() - timedelta(days=7)}
                }),
                "total_performance_issues": self.performance_issues.count_documents({}),
                "unresolved_issues": self.performance_issues.count_documents({
                    "action_implemented": False
                }),
                "database_storage_mb": self._get_collection_size_mb()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {}
    
    def _get_collection_size_mb(self) -> float:
        """Get approximate memory usage in MB"""
        try:
            stats = self.db.command("collStats", "investigations")
            size_bytes = stats.get("size", 0)
            return round(size_bytes / (1024 * 1024), 2)
        except:
            return 0.0