"""Data models for MongoDB queries and analysis"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueType(str, Enum):
    MISSING_INDEX = "missing_index"
    INEFFICIENT_QUERY = "inefficient_query"
    HIGH_EXAMINATION_RATIO = "high_examination_ratio"
    REGEX_WITHOUT_ANCHOR = "regex_without_anchor"
    NO_LIMIT = "no_limit"
    WHERE_CLAUSE = "where_clause"
    COLLECTION_SCAN = "collection_scan"


class SlowQuery(BaseModel):
    """Represents a slow query found in profiler data"""
    timestamp: datetime
    collection: str
    operation: str
    query: Dict[str, Any]
    execution_time_ms: int
    docs_examined: int
    docs_returned: int
    index_used: Optional[str] = None
    
    
class ExplainPlan(BaseModel):
    """Represents MongoDB explain output"""
    query: Dict[str, Any]
    collection: str
    execution_stats: Dict[str, Any]
    winning_plan: Dict[str, Any]
    execution_time_ms: int
    total_docs_examined: int
    total_docs_returned: int
    index_used: Optional[str] = None
    stage: str
    

class IndexInfo(BaseModel):
    """Represents MongoDB index information"""
    name: str
    keys: Dict[str, int]
    collection: str
    size_bytes: Optional[int] = None
    usage_count: Optional[int] = None


class Issue(BaseModel):
    """Represents a performance issue found by the agent"""
    type: IssueType
    severity: Severity
    collection: str
    title: str
    description: str
    query_pattern: Dict[str, Any]
    metrics: Dict[str, Any]  # execution time, docs examined, etc.
    root_cause: str
    

class Recommendation(BaseModel):
    """Represents an actionable recommendation"""
    issue: Issue
    priority: Severity
    command: str
    explanation: str
    expected_improvement: str
    impact_assessment: str
    
    
class AnalysisResult(BaseModel):
    """Complete analysis result from the agent"""
    timestamp: datetime
    investigation_summary: str
    slow_queries_analyzed: int
    issues_found: List[Issue]
    recommendations: List[Recommendation]
    total_investigation_time: float
    health_score: Optional[int] = None